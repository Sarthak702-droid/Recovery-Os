const BASE_URL=process.env.NEXT_PUBLIC_API_URL||'http://localhost:8001/api/v1';
export class ApiError extends Error {constructor(public status:number,message:string){super(message)}}
export async function api<T>(path:string,init?:RequestInit):Promise<T>{const response=await fetch(`${BASE_URL}${path}`,{...init,headers:{'Content-Type':'application/json',...init?.headers}});if(!response.ok)throw new ApiError(response.status,`Request failed (${response.status})`);return response.json() as Promise<T>}
