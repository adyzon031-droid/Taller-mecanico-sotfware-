import { DireccionFacade, opcionesColoniasUnicas } from './direccionFacade.js';

const { defineComponent } = window.Vue;

export const DireccionFields = defineComponent({
  name: 'DireccionFields',
  props: { modelValue: { type: Object, required: true }, direccionFacade: { type: Object, default: () => new DireccionFacade() }, title: { type: String, default: 'Dirección' }, fieldPrefix: { type: String, default: '' }, errorPrefix: { type: String, default: '' }, errors: { type: Object, default: () => ({}) }, required: { type: Boolean, default: false } },
  emits: ['update:modelValue'],
  data() { return { draft: null, pendingDraft: null, estados: [], municipios: [], filas: [], consulta: '', cargando: false, mensaje: '', noEncontrado: false, abierto: false, manual: false, cpController: null, catalogController: null, timer: null, ready: false }; },
  computed: {
    uniqueColonias() { return opcionesColoniasUnicas(this.filas); },
    filteredColonias() { const q = this.consulta.trim().toLocaleLowerCase('es-MX'); return this.uniqueColonias.filter(x => !q || x.colonia.toLocaleLowerCase('es-MX').includes(q)).slice(0, 100); },
    codesForColony() { const name = this.address.colonia; return [...new Set(this.filas.filter(x => x.colonia === name).map(x => x.cp).filter(Boolean))].sort(); },
    address() { const source = this.draft || this.modelValue; const x = {}; for (const key of ['calle','numero_interior','colonia','municipio','estado','codigo_postal','colonia_manual']) x[key] = source[this.fieldPrefix + key] ?? (key === 'colonia_manual' ? false : ''); return x; },
  },
  watch: { modelValue: { deep: true, handler(value) {
    if (this.pendingDraft) {
      const keys = new Set([...Object.keys(value || {}), ...Object.keys(this.pendingDraft)]);
      const acknowledged = [...keys].every(key => value?.[key] === this.pendingDraft[key]);
      if (!acknowledged) return;
      this.pendingDraft = null;
    }
    this.draft = { ...value };
    if (!this.ready) return;
    const name = this.address.colonia; this.manual = Boolean(this.address.colonia_manual); if (!this.manual && name && !this.abierto) this.consulta = name;
  } } },
  async mounted() {
    this.draft = { ...this.modelValue };
    try { const r = await this.direccionFacade.estados(); this.estados = r.estados || []; }
    catch (_) { this.mensaje = 'No se pudo cargar el catálogo de ubicaciones.'; }
    const a = this.address;
    this.manual = Boolean(a.colonia_manual);
    if (/^\d{5}$/.test(a.codigo_postal)) await this.lookupCp(a.codigo_postal, false);
    else if (a.estado && a.municipio) await this.loadMunicipality(a.estado, a.municipio);
    this.consulta = a.colonia || '';
    this.ready = true;
  },
  beforeUnmount() { clearTimeout(this.timer); this.cpController?.abort(); this.catalogController?.abort(); },
  methods: {
    set(key, value) { this.setMany({ [key]: value }); },
    setMany(values) {
      const next = { ...(this.draft || this.modelValue) };
      for (const [key, value] of Object.entries(values)) next[this.fieldPrefix + key] = value;
      this.draft = next;
      this.pendingDraft = next;
      this.$emit('update:modelValue', { ...next });
    },
    err(key) { return this.errors[this.errorPrefix + key] || ''; },
    clearColony(clearCp = true) { this.setMany({ colonia: '', colonia_manual: false, ...(clearCp ? { codigo_postal: '' } : {}) }); this.manual = false; this.consulta = ''; this.abierto = false; this.filas = []; },
    async lookupCp(cp, clear = true) {
      clearTimeout(this.timer); this.cpController?.abort();
      if (clear) { this.setMany({ estado: '', municipio: '', colonia: '', colonia_manual: false }); this.manual = false; this.consulta = ''; this.abierto = false; this.filas = []; }
      this.noEncontrado = false; this.mensaje = '';
      if (!/^\d{5}$/.test(cp)) return;
      this.timer = setTimeout(async () => {
        this.cpController = new AbortController(); this.cargando = true;
        try {
          const data = await this.direccionFacade.codigoPostal(cp, this.cpController.signal);
          this.filas = (data.colonias || []).map(x => ({ ...x, cp })); this.municipios = data.municipios || [];
          this.setMany({ estado: data.estados?.length === 1 ? data.estados[0] : '', municipio: this.municipios.length === 1 ? this.municipios[0] : '', colonia: '', colonia_manual: false });
          if (this.municipios.length > 1) this.mensaje = 'El código postal abarca varios municipios; elige uno.';
        } catch (e) { if (e.name !== 'AbortError') { this.noEncontrado = e.status === 404; this.mensaje = this.noEncontrado ? '' : 'No se pudo consultar el código postal.'; } }
        finally { if (!this.cpController?.signal.aborted) this.cargando = false; }
      }, 250);
    },
    async chooseState(value) { this.catalogController?.abort(); this.catalogController = new AbortController(); this.setMany({ estado: value, municipio: '', colonia: '', colonia_manual: false, codigo_postal: '' }); this.manual = false; this.consulta = ''; this.abierto = false; this.filas = []; this.municipios=[]; if (!value) return; this.cargando=true; try { const r=await this.direccionFacade.municipios(value,this.catalogController.signal); this.municipios=r.municipios||[]; } catch(e) { if(e.name!=='AbortError')this.mensaje='No se pudieron cargar los municipios.'; } finally { if(!this.catalogController.signal.aborted)this.cargando=false; } },
    async loadMunicipality(state, municipality) { this.catalogController?.abort(); this.catalogController=new AbortController(); this.cargando=true; try { const r=await this.direccionFacade.colonias(state,municipality,'',this.catalogController.signal); this.filas=(r.colonias||[]).map(x=>({...x,cp:String(x.cp||'')})); this.municipios=[municipality]; } catch(e) { if(e.name!=='AbortError')this.mensaje='No se pudieron cargar las colonias.'; } finally { if(!this.catalogController.signal.aborted)this.cargando=false; } },
    async chooseMunicipality(value) { const cpRows=this.filas.filter(x=>x.cp===this.address.codigo_postal&&x.municipio===value); const state=this.address.estado; this.setMany({ municipio: value, colonia: '', colonia_manual: false, codigo_postal: '' }); this.manual = false; this.consulta = ''; this.abierto = false; if(cpRows.length){this.filas=cpRows;return;} if(state&&value)await this.loadMunicipality(state,value); },
    chooseColony(row) { const matches=this.filas.filter(x=>x.colonia===row.colonia); this.set('colonia',row.colonia); this.set('estado',row.estado||this.address.estado); this.set('municipio',row.municipio||this.address.municipio); this.set('colonia_manual',false); this.manual=false; this.consulta=row.colonia; this.abierto=false; const cps=[...new Set(matches.map(x=>x.cp).filter(Boolean))]; this.set('codigo_postal',cps.length===1?cps[0]:''); this.mensaje=''; },
    manualMode() { this.clearColony(true); this.manual=true; this.set('colonia_manual',true); this.abierto=false; },
    async searchColony() { this.abierto=true; if(!this.address.estado||!this.address.municipio)return; clearTimeout(this.timer); this.catalogController?.abort(); this.catalogController=new AbortController(); this.cargando=true; try { const r=await this.direccionFacade.colonias(this.address.estado,this.address.municipio,this.consulta,this.catalogController.signal); this.filas=(r.colonias||[]).map(x=>({...x,cp:String(x.cp||'')})); } catch(e) { if(e.name!=='AbortError')this.mensaje='No se pudo buscar la colonia.'; } finally { if(!this.catalogController.signal.aborted)this.cargando=false; } },
    inputCp(event) { const cp=event.target.value.replace(/\D/g,'').slice(0,5); this.set('codigo_postal',cp); this.lookupCp(cp,true); },
    async chooseCode(cp) { this.set('codigo_postal',cp); },
  },
  template: `<div class="direccion-fields"><h3 class="form-section wide">{{title}}</h3>
    <label>Calle{{required?' *':''}}<input class="field" :value="address.calle" @input="set('calle',$event.target.value)"><small class="field-error">{{err('calle')}}</small></label>
    <label>Número interior<input class="field" :value="address.numero_interior" @input="set('numero_interior',$event.target.value)"></label>
    <label>Código postal{{required?' *':''}}<input class="field" inputmode="numeric" maxlength="5" :value="address.codigo_postal" @input="inputCp" :aria-invalid="noEncontrado"><small v-if="cargando" class="muted" role="status">Consultando ubicación…</small><small v-if="noEncontrado" class="field-error">Código postal no encontrado</small><small v-else class="field-error">{{err('codigo_postal')}}</small><select v-if="codesForColony.length>1&&!address.codigo_postal" class="field" aria-label="Elige el código postal" @change="chooseCode($event.target.value)"><option value="">Elige el código postal</option><option v-for="cp in codesForColony" :key="cp" :value="cp">{{cp}}</option></select></label>
    <label>Estado{{required?' *':''}}<select class="field" :value="address.estado" @change="chooseState($event.target.value)"><option value="">Selecciona un estado</option><option v-for="state in estados" :key="state" :value="state">{{state}}</option></select><small class="field-error">{{err('estado')}}</small></label>
    <label>Municipio{{required?' *':''}}<select v-if="municipios.length" class="field" :value="address.municipio" @change="chooseMunicipality($event.target.value)"><option value="">Selecciona un municipio</option><option v-for="mun in municipios" :key="mun" :value="mun">{{mun}}</option></select><input v-else class="field" :value="address.municipio" @input="set('municipio',$event.target.value)"><small class="field-error">{{err('municipio')}}</small></label>
    <label>Colonia{{required?' *':''}}<input v-if="manual" class="field" :value="address.colonia" placeholder="Escribe el nombre de la colonia" @input="set('colonia',$event.target.value)"><div v-else class="colony-picker"><input class="field" v-model="consulta" autocomplete="off" placeholder="Buscar colonia por nombre" :aria-expanded="abierto" @focus="abierto=true" @input="searchColony" @keydown.esc="abierto=false"><div v-if="abierto" class="colony-options" role="listbox"><button v-for="row in filteredColonias" :key="row.colonia+'-'+row.cp+'-'+row.municipio" type="button" class="colony-option" role="option" @click="chooseColony(row)">{{row.colonia}}</button><p v-if="!filteredColonias.length" class="colony-empty">{{address.estado&&address.municipio?'Sin colonias para esta ubicación.':'Elige estado y municipio o escribe un código postal.'}}</p><button type="button" class="colony-manual" @click="manualMode">Mi colonia no aparece</button></div></div><small class="field-error">{{err('colonia')}}</small><button v-if="manual" type="button" class="text-link" @click="manual=false;set('colonia_manual',false);set('colonia','')">Volver al catálogo</button></label>
    <p v-if="mensaje" class="wide muted" role="status">{{mensaje}}</p></div>`,
});
