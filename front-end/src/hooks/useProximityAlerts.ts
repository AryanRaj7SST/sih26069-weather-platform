import { useEffect, useState } from 'react';
import { realtimeService } from '@/services/realtimeService';
import { useLocationScope } from '@/hooks/useLocationScope';

export interface ProximityAlert {
  id: string;
  title: string;
  category: string;
  severity: string;
  distanceKm: number;
  timestamp: string;
}

export function useProximityAlerts(radiusKm: number = 25.0) {
  const { currentLocation } = useLocationScope();
  const [activeAlert, setActiveAlert] = useState<ProximityAlert | null>(null);

  useEffect(() => {
    const userLat = currentLocation.lat || 12.9716;
    const userLng = currentLocation.lon || 77.5946;

    const unsubscribe = realtimeService.subscribe((event) => {
      if (
        event.event_type === 'report.created' ||
        event.event_type === 'report.verification_changed' ||
        event.event_type === 'report.intelligence_ready'
      ) {
        const payload = event.payload as Record<string, unknown>;
        const lat = (payload?.latitude as number) || (payload?.lat as number);
        const lng = (payload?.longitude as number) || (payload?.lng as number);

        if (typeof lat === 'number' && typeof lng === 'number') {
          const dLat = (lat - userLat) * 111.0;
          const dLng = (lng - userLng) * 111.0 * Math.cos((userLat * Math.PI) / 180);
          const dist = Math.sqrt(dLat * dLat + dLng * dLng);

          if (dist <= radiusKm) {
            setActiveAlert({
              id: (payload?.id as string) || (payload?.report_id as string) || String(Date.now()),
              title: (payload?.title as string) || (payload?.category_code as string) || 'Nearby Weather Emergency',
              category: (payload?.category_code as string) || 'WEATHER_ALERT',
              severity: (payload?.severity as string) || 'HIGH',
              distanceKm: Math.round(dist * 10) / 10,
              timestamp: new Date().toLocaleTimeString(),
            });
          }
        }
      }
    });

    return () => {
      unsubscribe();
    };
  }, [currentLocation, radiusKm]);

  const dismissAlert = () => setActiveAlert(null);

  return { activeAlert, dismissAlert };
}
