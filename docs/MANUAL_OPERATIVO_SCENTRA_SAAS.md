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

## 26. Incidente: app caida por pool PostgreSQL

Sintoma en logs:

`QueuePool limit of size 5 overflow 10 reached, connection timed out`

Que significa:

- la API intento abrir mas conexiones PostgreSQL de las disponibles en su pool;
- cuando el pool se llena, endpoints simples como `/auth/refresh` tambien fallan;
- en navegador puede verse como 500 o incluso como error CORS si el backend no responde sano.

Fuentes de carga detectadas en codigo:

- Inbox visible hacia polling cada 5-8 segundos.
- Cada ciclo de Inbox podia pedir conversaciones, comentarios, agentes y hasta 7 endpoints de la conversacion abierta.
- Advisor flotante refresca senales cada 30-60 segundos.
- API puede ejecutar worker embebido.
- Worker standalone tambien puede ejecutar las mismas colas.

Politica operativa actualizada:

- Inbox debe hacer polling ligero para mensajes/estados y reservar memoria, multimodal, dedupe y busqueda para apertura/manual refresh.
- Worker embebido y worker standalone no deberian correr agresivos al mismo tiempo en produccion.
- En Compose, si existe servicio `worker`, el API debe preferir `SAAS_EMBEDDED_WORKER_ENABLED=false`.
- Para VPS pequeno, usar valores conservadores:
  - `SAAS_WORKER_IDLE_SEC=10`
  - `SAAS_WORKER_BATCH_SIZE=10`
  - `SAAS_DB_POOL_SIZE=10`
  - `SAAS_DB_MAX_OVERFLOW=20`

## 27. Polling: que refresca cada cosa

Cliente:

- `Inbox`: refresca conversaciones y la conversacion seleccionada de forma periodica mientras la pestana esta visible.
- `Advisor`: refresca senales globales si hay sesion activa; es mas frecuente cuando la ventana Advisor esta abierta.
- `Settings`: carga varios bloques al entrar, pero no deberia hacer polling continuo.
- `Intelligence`: algunas vistas tienen refresco interno de estado, especialmente realtime/preview.

Backend:

- `api-embedded-worker`: procesa webhooks, triggers, remarketing, IA, orquestador, outbound, billing, intelligence, reliability y tokens Meta cuando esta activo.
- `worker`: hace lo mismo como proceso separado.
- Si ambos estan activos, el diseno es idempotente, pero aumenta carga DB. En produccion pequena conviene elegir uno como principal.

## 28. Errores 403 de media WhatsApp

Rutas tipicas:

- `/saas/v1/media/whatsapp/{media_id}?token=...`

Que significa:

- Scentra si conoce el `media_id`, pero al pedir el archivo a Meta, Meta responde sin permiso o no accesible;
- causas comunes: token Meta vencido/revocado, WABA/phone number distinto, media expirada, media pertenece a otro activo, permisos `whatsapp_business_messaging` insuficientes.

Accion:

1. Ir a `Configuracion -> Diagnostico`.
2. Revisar `Token Meta guardado` y salud del token.
3. Probar con un audio/imagen nueva, no con media antigua.
4. Si solo falla media vieja, probablemente expiro o ya no es accesible desde Meta.
5. Si falla media nueva, revisar token/permisos/WABA.

La UI debe evitar reintentar indefinidamente un media que ya fallo para no llenar la consola.

## 29. Knowledge Base: `knowledge_file_too_large`

El upload de Knowledge acepta archivos hasta 8 MB.

Si aparece `knowledge_file_too_large`:

- dividir el PDF;
- exportar CSV/TXT mas pequeno;
- quitar imagenes pesadas del PDF;
- subir una URL publica si aplica;
- resumir documentos extensos en varios archivos.

La Knowledge Base no es almacenamiento bruto; su objetivo es texto util para RAG y respuestas IA.

## 30. Productos WooCommerce en Inbox y WhatsApp

En Scentra:

- el mensaje se guarda como tipo `product`;
- la tarjeta debe mostrar imagen completa en un bloque superior;
- el cuerpo debe mostrar nombre, precio, chips y boton `Ver producto` sin superponerse sobre la imagen.
- si la foto del producto tiene fondo transparente, la UI separa imagen y cuerpo en dos filas para que la foto no tape texto.

En WhatsApp cliente:

- si el producto tiene `image_url` publica, Scentra intenta enviarlo como imagen con caption;
- el caption incluye nombre, categoria, aromas/atributos, precio, link del producto y foto real;
- si Meta rechaza la imagen remota, Scentra envia el mismo contenido como texto fallback.

Riesgo:

- algunos formatos remotos de WooCommerce, como ciertos `.webp`, pueden no ser aceptados por Meta como media link. Para garantizar imagen siempre, se necesitara una etapa futura de descarga/conversion/subida controlada.

## 31. IA, triggers y plantillas

La IA conversacional no "activa plantillas" por decision propia.

Orden real:

1. Entra un mensaje por webhook.
2. Backend/worker evalua triggers y flows.
3. Si un trigger matchea y tiene `block_ai=true`, la IA no responde.
4. Si el trigger envia plantilla o flujo, eso lo hace backend, no el LLM.
5. Si no hay bloqueo, se agenda IA general o agente asignado.
6. La IA genera texto usando contexto, memoria, CRM y Knowledge/RAG.
7. Outbound envia la respuesta generada.

Visibilidad en Inbox:

- triggers internos, broadcasts y mensajes manuales deben crear un mensaje local en `saas_messages`;
- si una cola outbound antigua llega sin `message_id`, el dispatch crea una burbuja local antes de enviar al proveedor;
- por eso, si WhatsApp recibe una plantilla pero el Inbox no la muestra despues del redeploy, revisar si el envio salio desde una ruta externa/no registrada o si la conversacion activa no coincide con el destinatario.

Plantillas:

- Meta templates se usan en broadcasts, campanas, triggers y flujos.
- Deben estar aprobadas por Meta para enviarse fuera de ventana o como broadcast.
- La IA puede sugerir, pero no debe saltarse preflight, aprobacion ni reglas de Meta.

## 32. True AI / AI Premium

En codigo no existe una feature literal llamada `true_ai`. Lo mas cercano es el conjunto premium:

- `ai_premium`
- `ml_predictions`
- `lead_scoring_ml`
- `churn_prediction`
- `smart_remarketing`
- `ai_operational_intelligence`
- `advanced_analytics`
- features multimodales y agentes avanzados

Por que puede no dejar activar:

- el plan del tenant no incluye esa feature;
- Admin no habilito el feature flag para empresa/plan;
- esta en demo mode y no en full mode;
- hay cuotas agotadas;
- el proveedor/modelo requerido no tiene credencial usable;
- el agente/workflow no aprobo preflight;
- la accion requiere aprobacion humana.

Como habilitar:

1. Entrar al Admin SaaS.
2. Abrir tenant.
3. Revisar plan, feature flags y grants AI.
4. Activar `ai_premium` o la feature especifica.
5. Revisar cuotas/proveedor.
6. Volver al cliente y refrescar la vista.
