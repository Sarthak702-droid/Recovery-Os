'use client';
import {useQuery} from '@tanstack/react-query';
import {recoverosApi} from '@/lib/api/recoveros'; import {queryKeys} from '@/lib/query/keys';
import {ErrorState,LoadingState} from '@/components/shared/states'; import {StatusBadge} from '@/components/shared/ui';
export default function Health(){
 const q=useQuery({queryKey:queryKeys.health,queryFn:recoverosApi.health,retry:false,refetchInterval:30000});
 if(q.isLoading)return <main className="page"><LoadingState/></main>;
 if(q.isError||!q.data)return <main className="page"><ErrorState title="System health endpoint unavailable"/></main>;
 const entries=Object.entries(q.data);
 return <main className="page"><header className="page-head"><div><div className="eyebrow">Infrastructure monitoring</div><h1 className="page-title">System health</h1><p className="page-subtitle">Live backend probes refresh every 30 seconds. Unprobed dependencies are never reported healthy.</p></div></header><section className="status-grid">{entries.map(([name,value])=>{const latency='latency_ms' in value?value.latency_ms:undefined;return <div className="health-card card" key={name}><h3>{name.replaceAll('_',' ')}</h3><StatusBadge value={value.status}/><p>{latency!==undefined?<>Current latency: <strong style={{color:'white'}}>{latency} ms</strong></>:value.status==='NOT_EXPOSED'?'Backend health probe has not been implemented.':'Current backend-reported status.'}</p></div>})}</section></main>
}
