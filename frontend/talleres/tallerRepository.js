export class TallerRepository {
  constructor(baseUrl=window.API_BASE_URL||''){this.baseUrl=baseUrl}
  async request(path,options={}){const response=await fetch(this.baseUrl+path,{credentials:'include',...options,headers:options.body instanceof FormData?options.headers:{'Content-Type':'application/json',...options.headers}});const data=await response.json().catch(()=>({}));if(!response.ok){const e=new Error(data.error||'Error HTTP '+response.status);e.status=response.status;e.errors=data.errors||{};throw e}return data}
  listar(filters={}){return this.request('/api/talleres?'+new URLSearchParams(filters))}
  consultar(id){return this.request('/api/talleres/'+encodeURIComponent(id))}
  crear(data){return this.request('/api/talleres',{method:'POST',body:JSON.stringify(data)})}
  actualizar(id,data){return this.request('/api/talleres/'+encodeURIComponent(id),{method:'PUT',body:JSON.stringify(data)})}
  estado(id,activo,motivo=''){return this.request('/api/talleres/'+encodeURIComponent(id)+'/estado',{method:'PATCH',body:JSON.stringify({activo,motivo})})}
  foto(id,file){const body=new FormData();body.append('foto',file);return this.request('/api/talleres/'+encodeURIComponent(id)+'/foto',{method:'POST',body})}
  fotoUrl(id){return this.baseUrl+'/api/talleres/'+encodeURIComponent(id)+'/foto'}
}
