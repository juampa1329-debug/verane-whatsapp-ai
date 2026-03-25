# Formato Tecnico Unificado

## 1) Objetivo
Unificar en una sola arquitectura:

- CRM de mensajeria multicanal (WhatsApp, Facebook, Instagram, TikTok).
- Campanas CRM por canal (plantillas, triggers, remarketing, etapas).
- Ads Manager (campanas pagas y operacion tipo trafficker con apoyo IA).
- Ajustes operativos desde frontend (tokens, API keys, variables).
- Seguridad integral (usuarios, roles, 2FA, auditoria, politicas).

## 2) Principio clave de separacion de modulos

### Modulo A: Campanas CRM
Este modulo maneja comunicaciones con clientes y automatizaciones de CRM.

- Seccion propia para:
  - Plantillas.
  - Triggers.
  - Flujos de remarketing por etapas.
  - Campanas CRM de alcance segmentado.
- Contenido por canal es independiente:
  - Una plantilla creada en Instagram no aparece en Facebook o WhatsApp por defecto.
  - Debe existir accion explicita "Copiar a otro canal" para replicar.

### Modulo B: Ads Manager
Este modulo es separado de CRM y se enfoca en anuncios pagados.

- Gestion de campanas de anuncios por red social.
- Operacion de comentarios de anuncios.
- Mensajeria directa de redes sociales ligada a ads.
- Politicas de aprobacion para acciones IA (presupuesto, pausas, activaciones, cambios de audiencia).

## 3) Inbox multicanal (ventana de chats)

- Una ventana de chat unica con pestanas por canal:
  - WhatsApp
  - Facebook
  - Instagram
  - TikTok
- Cada pestana filtra conversaciones del canal correspondiente.
- Debe soportar:
  - Mensajes de texto.
  - Adjuntos (imagen, video, audio, documento) segun capacidad del canal.
  - Etiquetas CRM compartidas.
  - Toma de control humano (takeover).

## 4) Campanas CRM por canal

### Entidades principales
- `crm_template`
- `crm_trigger`
- `crm_flow`
- `crm_flow_step`
- `crm_campaign`
- `crm_enrollment`

Todas deben incluir `channel` (`whatsapp|facebook|instagram|tiktok`) como campo obligatorio.

### Reglas funcionales
- Filtros vacios significan "todos" para ese campo.
- Filtros con valor aplican restriccion exacta o por lista activa.
- Cada step del flow debe poder:
  - Editarse.
  - Dispararse individualmente.
- Cada flow debe poder:
  - Dispararse completo manualmente.
  - Ejecutarse automatico por motor de tiempo.

## 5) Remarketing por etapas

Estados recomendados:
- `stage_1`: primer contacto.
- `stage_2`: seguimiento intensivo.
- `stage_3`: cierre fuerte.
- `hold`: pausa temporal por respuesta o conversacion activa.
- `done`: terminado.
- `exited`: excluido por regla de salida.

Regla clave:
- Si el cliente responde, pasa a `hold` automaticamente.
- Si pasa el tiempo configurado sin respuesta, vuelve al flujo y avanza segun reglas.

## 6) Restriccion ventana WhatsApp (24h)

- El motor CRM debe validar la ventana de servicio antes de enviar.
- Si esta fuera de ventana:
  - detener envio directo.
  - encolar para plantilla aprobada (segun politica del canal).
- Configuracion visible en UI:
  - `resume_after_minutes`
  - `retry_minutes`
  - `service_window_hours`

## 7) Audio UX estilo WhatsApp

Requerimientos de interfaz:
- Iconos legibles y consistentes (sin caracteres corruptos).
- Grabacion de audio con forma de onda basada en nivel real de microfono.
- En chat, cada audio grabado debe renderizar su forma de onda.
- El usuario debe visualizar tiempo y estado de grabacion de forma clara.

## 8) Ajustes (frontend self-service)

Pestanas minimas en Ajustes:
- IA
- Variables/API
- Seguridad

### Variables/API
Permite gestionar desde frontend:
- Tokens por red social.
- API keys.
- Webhooks.
- Variables operativas no sensibles.

### Seguridad
- Usuarios y roles (RBAC).
- 2FA.
- Politicas de sesion.
- Auditoria de acciones criticas.

## 9) Seguridad y cumplimiento

- Hash de password: Argon2id o bcrypt (no SHA-256 simple para passwords).
- Cifrado de secretos: AES-256-GCM (o secreto gestionado por proveedor).
- JWT corto + refresh rotatorio.
- 2FA TOTP para admins.
- Log de auditoria inmutable por accion critica:
  - quien, cuando, que cambio, antes/despues.

## 10) Arquitectura recomendada

- `backend/app/crm/*` para logica CRM multicanal.
- `backend/app/ads/*` para Ads Manager.
- `backend/app/integrations/*` conectores (Meta/TikTok/WhatsApp/WooCommerce).
- `frontend/src/components/*` para paneles por modulo.
- `frontend/src/components/Settings*` para administracion de variables/seguridad.

## 11) Plan de implementacion por fases

### Fase 0 (actual)
- Esqueleto UI para:
  - Campanas CRM multicanal.
  - Ads Manager separado.
  - Tabs por canal en Inbox.
- Correcciones UX:
  - Iconos legibles.
  - Forma de onda real en grabacion y visualizacion de audio en chat.

### Fase 1
- Modelo de datos `channel` en entidades CRM.
- CRUD por canal para templates/triggers/flows/campaigns.
- Accion "Copiar a otro canal".

### Fase 2
- Motores automaticos:
  - Campaign engine.
  - Remarketing engine con hold/resume y reglas entrada/salida.
- Observabilidad y metricas por canal.

### Fase 3
- Integraciones sociales completas:
  - comentarios.
  - inbox DM.
  - webhooks por red.
- Ads IA con politicas de aprobacion y auditoria.

### Fase 4
- Hardening de seguridad:
  - 2FA obligatorio por rol.
  - rotacion de secretos.
  - reportes de auditoria.

## 12) Criterios de aceptacion

- El usuario visualiza dos modulos separados:
  - Campanas CRM.
  - Ads Manager.
- El usuario puede navegar por canal en Inbox y en CRM campañas.
- Los iconos del composer y chat son legibles.
- La forma de onda responde al nivel real de voz en grabacion.
- En mensajes de audio, la forma de onda se muestra en el chat.

## 13) Siguiente implementacion recomendada

1. Cerrar UI feedback del esqueleto (layout, tabs, labels).
2. Congelar contrato API por canal.
3. Migraciones DB para `channel` y tablas ads/auditoria.
4. Integrar webhooks por red social en orden: Meta -> TikTok.
