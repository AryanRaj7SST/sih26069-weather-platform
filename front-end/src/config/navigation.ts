import { UserRole } from "@/lib/roleRoutes";

export interface NavItem {
  id: string;
  labelKey: string;
  defaultLabel: string;
  path: string;
  iconName?: string;
  roles: UserRole[];
  group: "primary" | "more" | "mobile";
}

export const CITIZEN_PRIMARY_NAV: NavItem[] = [
  {
    id: "citizen-dashboard",
    labelKey: "nav.citizenArea",
    defaultLabel: "My Area",
    path: "/citizen-dashboard",
    iconName: "Home",
    roles: ["CITIZEN"],
    group: "primary",
  },
  {
    id: "report",
    labelKey: "nav.reportWeather",
    defaultLabel: "Report Event",
    path: "/report",
    iconName: "FileText",
    roles: ["CITIZEN"],
    group: "primary",
  },
  {
    id: "my-reports",
    labelKey: "nav.myReports",
    defaultLabel: "My Reports",
    path: "/my-reports",
    iconName: "FileText",
    roles: ["CITIZEN"],
    group: "primary",
  },
  {
    id: "live-map",
    labelKey: "nav.liveMap",
    defaultLabel: "Live Map",
    path: "/live-map",
    iconName: "Map",
    roles: ["CITIZEN"],
    group: "primary",
  },
  {
    id: "incidents",
    labelKey: "nav.incidents",
    defaultLabel: "Incidents",
    path: "/incidents",
    iconName: "AlertTriangle",
    roles: ["CITIZEN"],
    group: "primary",
  },
];

export const CITIZEN_MORE_NAV: NavItem[] = [
  {
    id: "national-map",
    labelKey: "nav.nationalMap",
    defaultLabel: "National Map",
    path: "/national-map",
    iconName: "Globe",
    roles: ["CITIZEN"],
    group: "more",
  },
  {
    id: "analytics",
    labelKey: "nav.analytics",
    defaultLabel: "Analytics",
    path: "/analytics",
    iconName: "BarChart3",
    roles: ["CITIZEN"],
    group: "more",
  },
  {
    id: "track-report",
    labelKey: "nav.trackReport",
    defaultLabel: "Track Report",
    path: "/track-report",
    iconName: "Search",
    roles: ["CITIZEN"],
    group: "more",
  },
];

export const CITIZEN_BOTTOM_NAV: NavItem[] = [
  {
    id: "b-my-area",
    labelKey: "nav.citizenArea",
    defaultLabel: "My Area",
    path: "/citizen-dashboard",
    iconName: "Home",
    roles: ["CITIZEN"],
    group: "mobile",
  },
  {
    id: "b-live-map",
    labelKey: "nav.liveMap",
    defaultLabel: "Live Map",
    path: "/live-map",
    iconName: "Map",
    roles: ["CITIZEN"],
    group: "mobile",
  },
  {
    id: "b-report",
    labelKey: "nav.reportWeather",
    defaultLabel: "Report",
    path: "/report",
    iconName: "AlertTriangle",
    roles: ["CITIZEN"],
    group: "mobile",
  },
  {
    id: "b-my-reports",
    labelKey: "nav.myReports",
    defaultLabel: "My Reports",
    path: "/my-reports",
    iconName: "FileText",
    roles: ["CITIZEN"],
    group: "mobile",
  },
  {
    id: "b-track",
    labelKey: "nav.trackReport",
    defaultLabel: "Track",
    path: "/track-report",
    iconName: "Search",
    roles: ["CITIZEN"],
    group: "mobile",
  },
];

export const STAFF_ADMIN_PRIMARY_NAV: NavItem[] = [
  {
    id: "dashboard",
    labelKey: "nav.dashboard",
    defaultLabel: "Operations Dashboard",
    path: "/dashboard",
    iconName: "LayoutDashboard",
    roles: ["ADMIN", "OPERATOR"],
    group: "primary",
  },
  {
    id: "verification-queue",
    labelKey: "nav.verificationQueue",
    defaultLabel: "Verification Queue",
    path: "/admin/queue",
    iconName: "CheckSquare",
    roles: ["ADMIN", "OPERATOR"],
    group: "primary",
  },
  {
    id: "audit-logs",
    labelKey: "nav.auditLogs",
    defaultLabel: "Audit Logs",
    path: "/admin/audit-logs",
    iconName: "ShieldCheck",
    roles: ["ADMIN", "OPERATOR"],
    group: "primary",
  },
  {
    id: "live-map",
    labelKey: "nav.liveMap",
    defaultLabel: "Live Map",
    path: "/live-map",
    iconName: "Map",
    roles: ["ADMIN", "OPERATOR"],
    group: "primary",
  },
  {
    id: "national-map",
    labelKey: "nav.nationalMap",
    defaultLabel: "National Map",
    path: "/national-map",
    iconName: "Globe",
    roles: ["ADMIN", "OPERATOR"],
    group: "primary",
  },
  {
    id: "incidents",
    labelKey: "nav.incidents",
    defaultLabel: "Incidents",
    path: "/incidents",
    iconName: "AlertTriangle",
    roles: ["ADMIN", "OPERATOR"],
    group: "primary",
  },
  {
    id: "analytics",
    labelKey: "nav.analytics",
    defaultLabel: "Analytics",
    path: "/analytics",
    iconName: "BarChart3",
    roles: ["ADMIN", "OPERATOR"],
    group: "primary",
  },
];

export const STAFF_OPERATOR_PRIMARY_NAV: NavItem[] = [
  {
    id: "verification-queue",
    labelKey: "nav.verificationQueue",
    defaultLabel: "Verification Queue",
    path: "/admin/queue",
    iconName: "CheckSquare",
    roles: ["OPERATOR", "ADMIN"],
    group: "primary",
  },
  {
    id: "dashboard",
    labelKey: "nav.dashboard",
    defaultLabel: "Operations Dashboard",
    path: "/dashboard",
    iconName: "LayoutDashboard",
    roles: ["OPERATOR", "ADMIN"],
    group: "primary",
  },
  {
    id: "audit-logs",
    labelKey: "nav.auditLogs",
    defaultLabel: "Audit Logs",
    path: "/admin/audit-logs",
    iconName: "ShieldCheck",
    roles: ["OPERATOR", "ADMIN"],
    group: "primary",
  },
  {
    id: "live-map",
    labelKey: "nav.liveMap",
    defaultLabel: "Live Map",
    path: "/live-map",
    iconName: "Map",
    roles: ["OPERATOR", "ADMIN"],
    group: "primary",
  },
  {
    id: "national-map",
    labelKey: "nav.nationalMap",
    defaultLabel: "National Map",
    path: "/national-map",
    iconName: "Globe",
    roles: ["OPERATOR", "ADMIN"],
    group: "primary",
  },
  {
    id: "incidents",
    labelKey: "nav.incidents",
    defaultLabel: "Incidents",
    path: "/incidents",
    iconName: "AlertTriangle",
    roles: ["OPERATOR", "ADMIN"],
    group: "primary",
  },
  {
    id: "analytics",
    labelKey: "nav.analytics",
    defaultLabel: "Analytics",
    path: "/analytics",
    iconName: "BarChart3",
    roles: ["OPERATOR", "ADMIN"],
    group: "primary",
  },
];

export const STAFF_ADMIN_MORE_NAV: NavItem[] = [
  {
    id: "track-report",
    labelKey: "nav.trackReport",
    defaultLabel: "Track Report",
    path: "/track-report",
    iconName: "Search",
    roles: ["ADMIN"],
    group: "more",
  },
];

export const STAFF_BOTTOM_NAV: NavItem[] = [
  {
    id: "b-dashboard",
    labelKey: "nav.dashboard",
    defaultLabel: "Dashboard",
    path: "/dashboard",
    iconName: "LayoutDashboard",
    roles: ["ADMIN", "OPERATOR"],
    group: "mobile",
  },
  {
    id: "b-queue",
    labelKey: "nav.verificationQueue",
    defaultLabel: "Queue",
    path: "/admin/queue",
    iconName: "CheckSquare",
    roles: ["ADMIN", "OPERATOR"],
    group: "mobile",
  },
  {
    id: "b-live-map",
    labelKey: "nav.liveMap",
    defaultLabel: "Live Map",
    path: "/live-map",
    iconName: "Map",
    roles: ["ADMIN", "OPERATOR"],
    group: "mobile",
  },
  {
    id: "b-analytics",
    labelKey: "nav.analytics",
    defaultLabel: "Analytics",
    path: "/analytics",
    iconName: "BarChart3",
    roles: ["ADMIN", "OPERATOR"],
    group: "mobile",
  },
  {
    id: "b-audit",
    labelKey: "nav.auditLogs",
    defaultLabel: "Audit",
    path: "/admin/audit-logs",
    iconName: "ShieldCheck",
    roles: ["ADMIN", "OPERATOR"],
    group: "mobile",
  },
];
