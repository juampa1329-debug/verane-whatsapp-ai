# Manual Operativo Scentra SaaS

Fecha de referencia: 2026-05-28  
Alcance: solo `saas-version/`

Este manual resume como operar Scentra desde el producto real detectado en codigo. No reemplaza la memoria tecnica del repositorio; sirve como guia de uso, diagnostico y entrenamiento para operacion diaria.

## 1. Flujo general del sistema

Scentra es un SaaS multi-tenant para atencion omnicanal, CRM conversacional, automatizacion, agentes IA, knowledge/RAG, inteligencia predictiva y administracion interna.

Flujo principal:

1. El cliente escribe por WhatsApp, Instagram, Facebook o un canal conectado.
2. Meta envia el evento al webhook de Scentra: `/saas/v1/webhooks/{provider}/{endpoint_key}`.
3. Scentra guarda el evento en `saas_webhook_events`.
4. El worker convierte el webhook en conversacion y mensaje.
5. El Inbox muestra el mensaje.
6. Triggers/flows pueden responder o bloquear IA con `block_ai`.
7. Si la IA esta activa y no hay bloqueo, se agenda una respuesta en cola IA.
8. El AI Gateway genera respuesta usando proveedor/modelo activo y fallbacks.
9. La respuesta se encola en outbound.
10. El worker outbound envia por Meta Cloud API.
11. Estados de entrega/lectura vuelven por webhook y se muestran en Inbox.

Si un mensaje no llega al Inbox, la IA no puede responder porque todavia no existe un mensaje entrante procesado.

## 2. Diagnostico urgente: no llegan mensajes o la IA no responde

Ruta en la app: `Configuracion -> Diagnostico`.

Orden recomendado:

1. Pulsa `Refrescar diagnostico`.
2. Envia un WhatsApp real desde el celular del cliente.
3. Mira `Ultimos webhooks`.
4. Si `Ultimos webhooks` queda vacio, Meta no esta llegando a Scentra. Revisa callback URL, verify token, WABA `subscribed_apps`, permisos y campo `messages` en Meta.
5. Pulsa `Verificar WABA subscribed_apps`.
6. Pulsa `Simular entrada`.
7. Si la simulacion crea mensaje en Inbox, el pipeline interno de Scentra funciona y el problema esta en Meta/configuracion externa.
8. Pulsa `Procesar pendientes` para forzar webhooks, IA y outbound pendientes.
9. Revisa `Colas y errores`:
   - `Webhooks received/error`: eventos entraron pero no procesaron.
   - `IA pending/failed`: la IA no genero respuesta.
   - `Outbound pending/failed`: la IA genero, pero el envio por Meta fallo.
10. Revisa `AI Gateway` para confirmar proveedor, modelo, latencia, tokens, fallback y errores.

Lectura rapida de sintomas:

- Hay statuses pero no inbound: Meta envia estados de mensajes salientes, pero no mensajes entrantes. Revisar WABA `subscribed_apps`, callback URL, verify token y campo `messages`.
- Simulacion OK pero WhatsApp real no entra: backend/worker estan bien; revisar Meta App/WABA.
- Mensaje entra pero IA no responde: revisar IA activa, API key, modelo activo, takeover humano, trigger con `block_ai`, agente asignado, presupuesto del agente, plan/cuotas.
- IA responde pero no sale a WhatsApp: revisar outbound, token Meta, phone number id, ventana de 24 horas, permisos de envio, limite del plan.
- Error 403 en media: puede ser token Meta, permisos, media expirada o tenant sin acceso correcto al media id.

## 3. Dashboard

Uso: vista ejecutiva del tenant.

Sirve para:

- ver conversaciones, mensajes, webhooks y consumo;
- revisar estado de plan/trial;
- detectar actividad reciente;
- confirmar que la empresa activa carga correctamente.

Si Dashboard da 500, normalmente hay drift de esquema o una tabla/columna faltante. Revisar `/saas/v1/ready` y migraciones.

## 4. Inbox

Uso: centro operativo de conversaciones.

Funciones:

- lista conversaciones por canal;
- filtros por busqueda, no leidos, asignadas, sin asignar, SLA, hot leads, takeover humano e IA;
- mensajes entrantes/salientes;
- adjuntos, audio, documentos, imagenes y producto WooCommerce;
- estados Meta;
- asignacion humana;
- asignacion de agente IA;
- panel CRM lateral;
- analisis multimodal y referencias visuales aprobadas.

Reglas operativas:

- La conversacion principal es la fuente canonica del historial. Por eso el CRM lateral no debe duplicar un timeline completo.
- Si se activa takeover humano, la IA no debe responder automatico.
- Si se asigna un agente IA especializado, la IA general deja de ser dueña de esa conversacion.
- Si se libera el agente IA, la conversacion vuelve a IA general si la IA del tenant esta activa.

## 5. Mini ficha CRM del Inbox

Uso: editar datos comerciales sin salir de la conversacion.

Incluye:

- datos del contacto;
- etapa CRM;
- prioridad, score, temperatura y SLA;
- asignacion humana;
- agente IA responsable;
- inteligencia predictiva;
- analisis de voz/vision/web;
- campos personalizados;
- tareas y follow-ups;
- duplicados;
- contexto IA;
- estados Meta.

Correccion aplicada:

- La tarjeta `Inteligencia predictiva` ahora ocupa el ancho completo de la mini ficha para evitar que aparezca comprimida.
- Los textos largos usan wrapping seguro para evitar solapes.

Notas internas:

- Las notas `IA:` se compactan backend-side para evitar que la IA reescriba la misma informacion una y otra vez.
- Las notas humanas se preservan.
- Si una ficha ya tenia ruido antiguo, abrir/guardar o permitir una nueva actualizacion IA ayuda a compactar duplicados.

## 6. CRM completo

Ruta: `Clientes`.

Sirve para:

- administrar fichas comerciales;
- configurar campos personalizados;
- aplicar pipelines por industria;
- crear etapas;
- editar clientes;
- manejar tareas;
- revisar duplicados.

Como nutrir el CRM:

- Completar nombre, telefono, ciudad, intereses, tipo de cliente, etapa, notas y campos personalizados.
- Usar etiquetas para segmentacion.
- Usar tareas para seguimiento.
- Evitar repetir informacion ya escrita en notas.

## 7. Etiquetas

Ruta: `Etiquetas`.

Sirven para:

- clasificar contactos y conversaciones;
- activar triggers;
- crear segmentos;
- filtrar oportunidades;
- alimentar remarketing.

Buenas practicas:

- usar etiquetas cortas y consistentes;
- no crear variantes duplicadas como `mayorista`, `Mayorista`, `mayoristas`;
- revisar efectos antes de borrar etiquetas usadas por triggers.

## 8. Campanas, triggers, flows y remarketing

Ruta: `Campanas`.

Sirve para:

- plantillas CRM;
- plantillas Meta;
- segmentos;
- triggers por palabras, comentarios, etiquetas, etapa, horario y estado;
- flows de remarketing;
- quiet hours;
- cooldown;
- simulador y preflight;
- A/B testing y versionado donde este disponible.

Reglas:

- Antes de activar un trigger/campana, usar simulador o preflight.
- Si un trigger debe responder primero, usar `block_ai` para que la IA no responda al mismo mensaje.
- Revisar cooldown para evitar spam.
- Validar plantillas WhatsApp aprobadas antes de enviar fuera de ventana.

## 9. Broadcast

Ruta: `Broadcast`.

Sirve para:

- envios masivos;
- plantillas Meta;
- destinatarios;
- reportes;
- export CSV.

Requisitos:

- Meta template aprobada si aplica;
- segmento correcto;
- plan/cuota disponible;
- token Meta valido;
- respeto por reglas anti-spam y ventana de WhatsApp.

## 10. Ads y Social

Ruta: `Ads`.

Sirve para:

- cuentas publicitarias;
- campañas;
- leads;
- comentarios;
- sugerencias IA para respuestas;
- procesamiento social de Instagram/Facebook.

Si no llegan comentarios o DMs:

- revisar permisos `pages_messaging`, `pages_manage_metadata`, `pages_read_engagement`, `instagram_manage_messages`;
- revisar `subscribed_apps` de la Page;
- revisar webhook de Instagram/Facebook en Diagnostico.

## 11. Agentes IA

Ruta: `AI Agents`.

Sirve para:

- crear y administrar agentes;
- usar agentes de fabrica;
- crear agentes personalizados;
- asignar herramientas;
- revisar memoria;
- revisar logs;
- controlar prompts, canales, workflows y metricas.

Asignacion:

- Manual: desde la mini ficha del Inbox en `Agente IA responsable`.
- Automatica: el orquestador puede asignar un agente segun contexto.
- Cuando un agente queda asignado, la IA general no debe competir por la respuesta.
- Al liberar el agente, la conversacion vuelve a IA general si esta activa.

Memoria:

- Cada agente puede tener memoria propia.
- Existe memoria colectiva/empresarial para contexto compartido.
- Al eliminar un agente, las memorias pueden quedar disponibles para revision/borrado posterior segun las politicas existentes.

## 12. Inteligencia

Ruta: `Intelligence`.

Incluye:

- predicciones;
- lead scoring;
- churn;
- smart remarketing;
- recomendaciones;
- Advisor;
- operaciones autonomas;
- Revenue Engine;
- Memory Network;
- Federated Learning;
- multimodal observability y rollout.

Reglas:

- Muchas funciones son premium-gated.
- Demo mode puede mostrar previews limitados.
- Acciones autonomas criticas requieren aprobacion o niveles de autonomia configurados.
- La inteligencia no debe compartir mensajes crudos entre tenants.

## 13. Ecosistema AI

Ruta: `Ecosystem`.

Incluye:

- marketplace de agentes;
- plugin center;
- tool registry;
- developer console;
- integraciones AI;
- mini AI apps.

Uso seguro:

- activar solo herramientas necesarias;
- revisar permisos antes de instalar plugins/agentes;
- no dar herramientas de envio/cambio de CRM sin aprobaciones claras.

## 14. Workflow Composer

Ruta: `Composer`.

Sirve para:

- diseñar workflows AI;
- componer pasos;
- preparar automatizaciones;
- revisar/validar antes de usar en runtime.

No asumir que un workflow diseñado queda automaticamente activo en produccion. Debe pasar por validacion, permisos y activacion correspondiente.

## 15. Trust Center

Ruta: `Trust`.

Sirve para:

- compliance;
- privacidad;
- auditoria;
- politicas AI;
- gobierno de herramientas;
- controles de riesgo.

Uso recomendado:

- revisar permisos de AI y acciones autonomas;
- export/delete requests si aplica;
- monitorear auditoria de acciones criticas.

## 16. Configuracion: IA

Ruta: `Configuracion -> IA`.

Sirve para:

- activar/desactivar IA;
- seleccionar proveedor y modelo;
- configurar fallback provider/model;
- system prompt;
- estilo de respuesta humana;
- dividir respuestas en fragmentos;
- limites de tokens;
- ventana de contexto reciente;
- indicador de escribiendo;
- voz/TTS;
- Knowledge Base.

Como activar IA correctamente:

1. Guardar credencial API del proveedor en `Configuracion -> APIs`.
2. Seleccionar proveedor/modelo en `Configuracion -> IA`.
3. Activar IA.
4. Configurar fallback.
5. Mantener `humanReplyStyle` y `humanReplySplitting` si se quieren respuestas naturales.
6. Verificar en `Diagnostico` que `API IA guardada` y `Modelo IA seleccionado` esten OK.

Como mantener contexto:

- El backend usa CRM, memoria de conversacion, facts, Knowledge/RAG, memoria colectiva, contexto multimodal aprobado y transcript reciente acotado.
- No conviene enviar historiales enormes en cada request porque sube costo/latencia.
- Para continuidad larga, nutrir CRM, Knowledge y memoria; no depender solo de mensajes recientes.

## 17. Configuracion: Vertical

Ruta: `Configuracion -> Vertical`.

Sirve para:

- seleccionar industria;
- aplicar packs verticales;
- adaptar pipelines, agentes, prompts, triggers y plantillas base.

Recomendacion:

- definir industria al crear la empresa;
- revisar el pipeline y campos tras aplicar un pack;
- no reaplicar packs sin revisar impacto en datos existentes.

## 18. Configuracion: Canales

Ruta: `Configuracion -> Canales`.

Incluye:

- WhatsApp Cloud API;
- Instagram Business;
- Facebook;
- WooCommerce;
- endpoints webhook.

WhatsApp minimo viable:

- `phone_number_id`;
- `business_account_id` o WABA ID;
- token Meta permanente/valido;
- app id si aplica;
- endpoint webhook activo;
- callback URL registrada en Meta;
- verify token correcto;
- subscribed_apps del WABA;
- campo `messages` habilitado.

## 19. Configuracion: APIs

Ruta: `Configuracion -> APIs`.

Sirve para:

- agregar credenciales AI;
- listar modelos del proveedor;
- configurar TTS;
- configurar busqueda web/imagen;
- configurar canales.

Reglas:

- No pegar secretos en notas ni chats.
- Si un proveedor falla, configurar fallback real en IA.
- Groq puede devolver 403 por bloqueo externo de Cloudflare/IP/proyecto; mantener otro proveedor activo.

## 20. Configuracion: Diagnostico

Ruta: `Configuracion -> Diagnostico`.

Panel clave para soporte:

- estado API/worker;
- IA activa;
- integraciones;
- webhooks;
- WABA subscribed_apps;
- simulacion inbound;
- colas;
- errores outbound;
- AI Gateway;
- ultimos webhooks.

Botones:

- `Refrescar diagnostico`: solo consulta estado.
- `Procesar pendientes`: ejecuta webhooks, IA y outbound pendientes.
- `Verificar WABA subscribed_apps`: consulta Meta para confirmar suscripcion.
- `Simular entrada`: inserta un webhook falso para probar pipeline interno.

## 21. Usuarios, perfil, seguridad y plan

Usuarios:

- gestion de equipo segun roles disponibles.

Perfil:

- datos visibles del usuario/empresa.

Seguridad:

- cambio de clave;
- MFA/2FA cuando este configurado;
- eventos de seguridad.

Plan:

- estado de trial/suscripcion;
- limites;
- billing;
- restricciones por impago o plan.

## 22. Admin SaaS

Admin separado del cliente.

Sirve para:

- tenants;
- planes;
- suscripciones;
- billing;
- creditos manuales;
- operations;
- observability;
- audit;
- intelligence premium gating;
- provider policies;
- performance/reliability;
- trust/security.

Reglas:

- usar admin para activar/desactivar empresas;
- controlar feature flags y planes desde admin;
- no editar datos productivos sin auditoria;
- revisar readiness antes de redeploy.

## 23. Checklist de produccion tras redeploy

1. API responde `/saas/v1/health`.
2. API responde `/saas/v1/ready` con 200.
3. Login tenant OK.
4. Registro demo OK.
5. Dashboard carga.
6. Inbox carga conversaciones.
7. `Configuracion -> Diagnostico` carga sin 500.
8. `Simular entrada` crea mensaje.
9. Enviar WhatsApp real crea mensaje en Inbox.
10. IA responde si esta activa.
11. Outbound envia a WhatsApp.
12. Estados Meta llegan.
13. Admin carga.
14. Worker no muestra errores repetidos.

## 24. Cuando pedir revision tecnica

Pedir revision si:

- `/ready` no pasa;
- login/register dan 500;
- webhooks quedan en `error`;
- `Ultimos webhooks` esta vacio aunque Meta dice entregado;
- hay `statuses_without_inbound`;
- IA queda en failed repetidamente;
- outbound falla con errores Meta;
- aparecen columnas/tablas faltantes en logs;
- una funcion premium da 403 y deberia estar habilitada;
- un agente responde junto con IA general;
- notas CRM vuelven a duplicarse masivamente.

## 25. Resumen rapido para el incidente actual

Por las capturas, el mensaje enviado desde WhatsApp no aparece como nuevo mensaje entrante en el Inbox. Eso indica revisar primero webhook/Meta:

1. Ir a `Configuracion -> Diagnostico`.
2. Refrescar.
3. Enviar WhatsApp real.
4. Ver `Ultimos webhooks`.
5. Si esta vacio, revisar Meta callback/subscription.
6. Ejecutar `Simular entrada`.
7. Si simulacion OK, Scentra esta procesando bien; el corte esta antes de Scentra.
8. Ejecutar `Verificar WABA subscribed_apps`.
9. Ejecutar `Procesar pendientes`.
10. Si el inbound entra pero no hay respuesta, revisar IA, triggers con `block_ai`, takeover humano y asignacion de agente.
