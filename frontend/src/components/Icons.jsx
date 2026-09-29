// Inline stroke icons — no icon package, so nothing is fetched at runtime.
const base = {
  width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none',
  stroke: 'currentColor', strokeWidth: 1.6, strokeLinecap: 'round',
  strokeLinejoin: 'round',
}
const Icon = ({ children, size = 18, ...rest }) => (
  <svg {...base} width={size} height={size} {...rest}>{children}</svg>
)

export const IconDashboard = (p) => (
  <Icon {...p}><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></Icon>
)
export const IconLibrary = (p) => (
  <Icon {...p}><path d="M4 4v16" /><path d="M8 4v16" /><path d="m12.5 4.6 4.3 15.5" /><path d="M20 20H4" /></Icon>
)
export const IconChat = (p) => (
  <Icon {...p}><path d="M21 12a8 8 0 0 1-8 8H7l-4 3v-6.5A8 8 0 0 1 11 4h2a8 8 0 0 1 8 8Z" /></Icon>
)
export const IconLab = (p) => (
  <Icon {...p}><path d="M9 3v6.5L4.4 17A2 2 0 0 0 6.1 20h11.8a2 2 0 0 0 1.7-3L15 9.5V3" /><path d="M8 3h8" /><path d="M7.5 14h9" /></Icon>
)
export const IconPulse = (p) => (
  <Icon {...p}><path d="M3 12h4l2.5-7 5 14L17 12h4" /></Icon>
)
export const IconLayers = (p) => (
  <Icon {...p}><path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="m3 13 9 5 9-5" /></Icon>
)
export const IconUpload = (p) => (
  <Icon {...p}><path d="M12 16V4" /><path d="m7 9 5-5 5 5" /><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" /></Icon>
)
export const IconSend = (p) => (
  <Icon {...p}><path d="M4 12 20 4l-7 16-2.5-6.5L4 12Z" /></Icon>
)
export const IconTrash = (p) => (
  <Icon {...p}><path d="M4 7h16" /><path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" /><path d="M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13" /></Icon>
)
export const IconDoc = (p) => (
  <Icon {...p}><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5Z" /><path d="M14 3v5h5" /></Icon>
)
export const IconImage = (p) => (
  <Icon {...p}><rect x="3" y="4" width="18" height="16" rx="2" /><circle cx="8.5" cy="9.5" r="1.5" /><path d="m4 17 5-5 4 4 3-2 4 4" /></Icon>
)
export const IconAudio = (p) => (
  <Icon {...p}><path d="M12 3v18" /><path d="M8 7v10" /><path d="M16 7v10" /><path d="M4 10v4" /><path d="M20 10v4" /></Icon>
)
export const IconMoon = (p) => (
  <Icon {...p}><path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z" /></Icon>
)
export const IconSun = (p) => (
  <Icon {...p}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4" /></Icon>
)
export const IconCheck = (p) => (
  <Icon {...p}><path d="m4 12.5 5 5L20 6.5" /></Icon>
)
export const IconX = (p) => (
  <Icon {...p}><path d="M6 6l12 12M18 6 6 18" /></Icon>
)
export const IconRefresh = (p) => (
  <Icon {...p}><path d="M20 11a8 8 0 1 0-1.8 6" /><path d="M20 4v7h-7" /></Icon>
)

export const modalityIcon = (m, props) =>
  m === 'image' ? <IconImage {...props} /> : m === 'audio' ? <IconAudio {...props} /> : <IconDoc {...props} />
