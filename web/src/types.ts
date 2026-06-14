export interface StreamerStatus {
  username: string;
  online: boolean;
  points: number;
  session_gained: number;
  title: string;
  game: string;
  drops_active: boolean;
  watch_streak: boolean;
}

export interface PredictionStatus {
  streamer: string;
  title: string;
  status: string;
  bet_placed: boolean;
}

export interface StatusSnapshot {
  running: boolean;
  username: string;
  session_id: string;
  uptime_seconds: number;
  session_points_gained: number;
  ws_connected: boolean;
  streamers: StreamerStatus[];
  predictions: PredictionStatus[];
}

export interface AnalyticsPoint {
  x: number;
  y: number;
  z: string;
}

export interface AnalyticsData {
  series: AnalyticsPoint[];
  annotations: AnalyticsPoint[];
}

export interface MetaInfo {
  days_ago: number;
  username: string;
}
