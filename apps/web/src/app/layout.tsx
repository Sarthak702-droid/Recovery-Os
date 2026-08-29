import './globals.css'; import {Providers} from './providers'; import {AppShell} from '@/components/layout/app-shell';
export const metadata={title:'RecoverOS | Revenue Recovery Operations',description:'Policy-gated revenue recovery platform'};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body><Providers><AppShell>{children}</AppShell></Providers></body></html>}
