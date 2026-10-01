export type UserRole = "CITIZEN" | "OPERATOR" | "ADMIN";

export function getHomeRouteForRole(role?: string | null): string {
  const normalized = (role || "").toUpperCase();
  if (normalized === "ADMIN") {
    return "/dashboard";
  }
  if (normalized === "OPERATOR") {
    return "/admin/queue";
  }
  return "/citizen-dashboard";
}

export function isStaff(role?: string | null): boolean {
  const normalized = (role || "").toUpperCase();
  return normalized === "ADMIN" || normalized === "OPERATOR";
}

export function isCitizen(role?: string | null): boolean {
  const normalized = (role || "").toUpperCase();
  return normalized === "CITIZEN";
}
