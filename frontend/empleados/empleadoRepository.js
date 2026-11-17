/** Único acceso HTTP para el módulo de personal. */
export class EmpleadoRepository {
  constructor(baseUrl=window.API_BASE_URL||''){this.baseUrl=baseUrl;}
  async request(path,{method='GET',body,query=''}={}){
    const form=body instanceof FormData;
    const response=await fetch(`${this.baseUrl}/api/empleados${path}${query}`,{method,credentials:'include',headers:form?{}:{'Content-Type':'application/json'},body:body?(form?body:JSON.stringify(body)):undefined});
    const data=await response.json().catch(()=>({}));
    if(!response.ok){const error=new Error(data.error||`Error HTTP ${response.status}`);error.status=response.status;error.errors=data.errors||{};throw error;}
    return data;
  }
  listar(filters){const q=new URLSearchParams(filters).toString();return this.request('',{query:`?${q}`});}
  talleres(){return this.request('/talleres');}
  consultar(id){return this.request(`/${encodeURIComponent(id)}`);}
  verificar(campo,valor,exclude){const q=new URLSearchParams({campo,valor,...(exclude?{excluir_id:String(exclude)}:{})}).toString();return this.request('/verificar-duplicado',{query:`?${q}`});}
  guardar(id,data,photo){const form=new FormData();form.append('empleado',JSON.stringify(data));if(photo)form.append('foto',photo);return this.request(id?`/${id}`:'',{method:id?'PUT':'POST',body:form});}
  estado(id,active,motivo=''){return this.request(`/${id}/${active?'reactivar':'baja'}`,{method:'PATCH',body:active?{}:{motivo}});}
  fotoUrl(id){return `${this.baseUrl}/api/empleados/${encodeURIComponent(id)}/foto`;}
}
