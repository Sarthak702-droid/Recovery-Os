import {AlertTriangle,DatabaseZap,Inbox} from 'lucide-react';
export function EmptyState({title,description}:{title:string;description:string}){return <div className="empty"><Inbox size={30} strokeWidth={1.5}/><strong>{title}</strong><span>{description}</span></div>}
export function ErrorState({title='Unable to load data',description='The API returned an error. Retry or check system health.'}:{title?:string;description?:string}){return <div className="error"><AlertTriangle size={30} strokeWidth={1.5}/><strong>{title}</strong><span>{description}</span></div>}
export function LoadingState(){return <div className="empty"><DatabaseZap size={28}/><strong>Loading live data</strong><span>Requesting the latest persisted RecoverOS records.</span></div>}
