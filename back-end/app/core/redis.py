import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisProtocolError(Exception):
    """Raised when Redis server returns an error or malformed RESP response."""

    pass


class AsyncRedisClient:
    """Zero-dependency, resilient asynchronous Redis client implementing RESP2/RESP3 protocol.

    Provides high-performance Redis Stream buffering and queuing primitives without
    external C-extension or binary driver dependencies.
    """

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self.redis_url = redis_url or settings.REDIS_URL
        parsed = urlparse(self.redis_url)
        self.host = parsed.hostname or "localhost"
        self.port = parsed.port or 6379
        self.db = int(parsed.path.lstrip("/") or "0")
        self.password = parsed.password

        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Establish asynchronous TCP socket connection to Redis server."""
        if self._writer is not None and not self._writer.is_closing():
            return

        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=5.0,
            )

            # Authenticate if password provided
            if self.password:
                await self._execute_raw("AUTH", self.password)

            # Select DB if not 0
            if self.db != 0:
                await self._execute_raw("SELECT", str(self.db))

        except Exception as e:
            self._reader = None
            self._writer = None
            raise ConnectionError(f"Could not connect to Redis at {self.host}:{self.port}: {e}")

    async def close(self) -> None:
        """Close Redis connection."""
        async with self._lock:
            if self._writer is not None:
                try:
                    self._writer.close()
                    await self._writer.wait_closed()
                except Exception:
                    pass
                self._writer = None
                self._reader = None

    def _encode_command(self, *args: Union[str, bytes, int, float]) -> bytes:
        """Encode command arguments into Redis RESP array format."""
        parts = [f"*{len(args)}\r\n".encode("utf-8")]
        for arg in args:
            if isinstance(arg, bytes):
                arg_bytes = arg
            else:
                arg_bytes = str(arg).encode("utf-8")
            parts.append(f"${len(arg_bytes)}\r\n".encode("utf-8"))
            parts.append(arg_bytes)
            parts.append(b"\r\n")
        return b"".join(parts)

    async def _read_response(self) -> Any:
        """Parse RESP response from server."""
        if self._reader is None:
            raise ConnectionError("Redis client is not connected.")

        line = await self._reader.readline()
        if not line:
            raise ConnectionError("Redis connection closed unexpectedly.")

        prefix = line[0:1]
        content = line[1:-2]  # Strip prefix and \r\n

        # Simple String (+)
        if prefix == b"+":
            return content.decode("utf-8", errors="replace")

        # Error (-)
        if prefix == b"-":
            err_msg = content.decode("utf-8", errors="replace")
            raise RedisProtocolError(err_msg)

        # Integer (:)
        if prefix == b":":
            return int(content)

        # Bulk String ($)
        if prefix == b"$":
            length = int(content)
            if length == -1:
                return None
            data = await self._reader.readexactly(length + 2)
            return data[:-2].decode("utf-8", errors="replace")

        # Array (*)
        if prefix == b"*":
            num_elements = int(content)
            if num_elements == -1:
                return None
            result: List[Any] = []
            for _ in range(num_elements):
                result.append(await self._read_response())
            return result

        raise RedisProtocolError(f"Unknown RESP prefix: {prefix!r}")

    async def _execute_raw(self, *args: Union[str, bytes, int, float]) -> Any:
        """Execute command over socket with connection safety and retry."""
        async with self._lock:
            await self.connect()
            assert self._writer is not None
            try:
                cmd_bytes = self._encode_command(*args)
                self._writer.write(cmd_bytes)
                await self._writer.drain()
                return await self._read_response()
            except (ConnectionError, asyncio.TimeoutError, OSError) as e:
                # Reset connection on transport failures
                self._writer = None
                self._reader = None
                raise ConnectionError(f"Redis transport failure: {e}")

    async def ping(self) -> bool:
        """Check Redis connectivity."""
        try:
            res = await self._execute_raw("PING")
            return res == "PONG" or res is True
        except Exception:
            return False

    async def xadd(
        self,
        stream: str,
        fields: Dict[str, Any],
        max_len: Optional[int] = None,
        approximate: bool = True,
    ) -> str:
        """Append an entry to a Redis stream."""
        cmd: List[Union[str, bytes, int, float]] = ["XADD", stream]
        if max_len is not None:
            cmd.extend(["MAXLEN", "~" if approximate else "=", str(max_len)])
        cmd.append("*")  # Auto-generate message ID

        for k, v in fields.items():
            cmd.append(str(k))
            cmd.append(str(v))

        msg_id = await self._execute_raw(*cmd)
        return str(msg_id)

    async def xgroup_create(
        self,
        stream: str,
        group: str,
        id_str: str = "$",
        mkstream: bool = True,
    ) -> bool:
        """Create a consumer group for a Redis stream."""
        cmd: List[Union[str, bytes, int, float]] = ["XGROUP", "CREATE", stream, group, id_str]
        if mkstream:
            cmd.append("MKSTREAM")
        try:
            res = await self._execute_raw(*cmd)
            return res == "OK"
        except RedisProtocolError as e:
            if "BUSYGROUP" in str(e):
                # Group already exists
                return True
            raise

    def _parse_stream_entries(self, raw_entries: Any) -> List[Tuple[str, Dict[str, str]]]:
        """Parse raw Redis list of stream entries into typed tuples.

        Expected format: [[id, [k1, v1, k2, v2, ...]], ...]
        """
        if not raw_entries or not isinstance(raw_entries, list):
            return []
        parsed: List[Tuple[str, Dict[str, str]]] = []
        for entry in raw_entries:
            if not isinstance(entry, list) or len(entry) < 2:
                continue
            m_id = str(entry[0])
            raw_fields = entry[1]
            f_dict: Dict[str, str] = {}
            if isinstance(raw_fields, list):
                for i in range(0, len(raw_fields), 2):
                    if i + 1 < len(raw_fields):
                        f_dict[str(raw_fields[i])] = str(raw_fields[i + 1])
            parsed.append((m_id, f_dict))
        return parsed

    async def xreadgroup(
        self,
        group: str,
        consumer: str,
        streams: Dict[str, str],
        count: Optional[int] = None,
        block_ms: Optional[int] = None,
    ) -> List[Tuple[str, List[Tuple[str, Dict[str, str]]]]]:
        """Read entries from a Redis stream via a consumer group.

        Returns list of (stream_name, list_of_(msg_id, fields_dict)).
        """
        cmd: List[Union[str, bytes, int, float]] = ["XREADGROUP", "GROUP", group, consumer]
        if count is not None:
            cmd.extend(["COUNT", str(count)])
        if block_ms is not None:
            cmd.extend(["BLOCK", str(block_ms)])

        cmd.append("STREAMS")
        for stream_name in streams.keys():
            cmd.append(stream_name)
        for msg_id in streams.values():
            cmd.append(msg_id)

        raw_response = await self._execute_raw(*cmd)
        if not raw_response or not isinstance(raw_response, list):
            return []

        parsed_streams: List[Tuple[str, List[Tuple[str, Dict[str, str]]]]] = []
        for stream_item in raw_response:
            if not isinstance(stream_item, list) or len(stream_item) < 2:
                continue
            stream_name = str(stream_item[0])
            entries_list = stream_item[1]
            parsed_entries = self._parse_stream_entries(entries_list)
            parsed_streams.append((stream_name, parsed_entries))

        return parsed_streams

    async def xread(
        self,
        streams: Dict[str, str],
        count: Optional[int] = None,
        block_ms: Optional[int] = None,
    ) -> List[Tuple[str, List[Tuple[str, Dict[str, str]]]]]:
        """Read entries from one or more Redis streams directly (standalone streaming/replay).

        Returns list of (stream_name, list_of_(msg_id, fields_dict)).
        """
        cmd: List[Union[str, bytes, int, float]] = ["XREAD"]
        if count is not None:
            cmd.extend(["COUNT", str(count)])
        if block_ms is not None:
            cmd.extend(["BLOCK", str(block_ms)])

        cmd.append("STREAMS")
        for stream_name in streams.keys():
            cmd.append(stream_name)
        for msg_id in streams.values():
            cmd.append(msg_id)

        raw_response = await self._execute_raw(*cmd)
        if not raw_response or not isinstance(raw_response, list):
            return []

        parsed_streams: List[Tuple[str, List[Tuple[str, Dict[str, str]]]]] = []
        for stream_item in raw_response:
            if not isinstance(stream_item, list) or len(stream_item) < 2:
                continue
            stream_name = str(stream_item[0])
            entries_list = stream_item[1]
            parsed_entries = self._parse_stream_entries(entries_list)
            parsed_streams.append((stream_name, parsed_entries))

        return parsed_streams

    async def xrange(
        self,
        stream: str,
        min_id: str = "-",
        max_id: str = "+",
        count: Optional[int] = None,
    ) -> List[Tuple[str, Dict[str, str]]]:
        """Fetch range of entries from stream in ascending order."""
        cmd: List[Union[str, bytes, int, float]] = ["XRANGE", stream, min_id, max_id]
        if count is not None:
            cmd.extend(["COUNT", str(count)])
        raw_response = await self._execute_raw(*cmd)
        return self._parse_stream_entries(raw_response)

    async def xrevrange(
        self,
        stream: str,
        max_id: str = "+",
        min_id: str = "-",
        count: Optional[int] = None,
    ) -> List[Tuple[str, Dict[str, str]]]:
        """Fetch range of entries from stream in descending order."""
        cmd: List[Union[str, bytes, int, float]] = ["XREVRANGE", stream, max_id, min_id]
        if count is not None:
            cmd.extend(["COUNT", str(count)])
        raw_response = await self._execute_raw(*cmd)
        return self._parse_stream_entries(raw_response)

    async def xack(self, stream: str, group: str, *ids: str) -> int:
        """Acknowledge one or more message IDs in a consumer group."""
        if not ids:
            return 0
        cmd: List[Union[str, bytes, int, float]] = ["XACK", stream, group]
        cmd.extend(ids)
        res = await self._execute_raw(*cmd)
        return int(res) if isinstance(res, int) else 0

    async def xpending(self, stream: str, group: str) -> Dict[str, Any]:
        """Fetch pending entries list (PEL) summary for a consumer group."""
        cmd: List[Union[str, bytes, int, float]] = ["XPENDING", stream, group]
        res = await self._execute_raw(*cmd)
        if not res or not isinstance(res, list) or len(res) < 4:
            return {"count": 0, "min_id": None, "max_id": None, "consumers": []}
        return {
            "count": int(res[0]) if res[0] is not None else 0,
            "min_id": res[1],
            "max_id": res[2],
            "consumers": res[3] if isinstance(res[3], list) else [],
        }

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys from Redis."""
        if not keys:
            return 0
        res = await self._execute_raw("DEL", *keys)
        return int(res) if isinstance(res, int) else 0


redis_client = AsyncRedisClient()
