package com.verane.mobile.core.network

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject

@Serializable
data class ApiOkResponse(
    val ok: Boolean = false,
)

@Serializable
data class GenericJsonResponse(
    val data: JsonObject? = null,
)

@Serializable
data class DashboardOverviewResponse(
    @SerialName("range_days") val rangeDays: Int = 0,
    val since: String? = null,
    val kpis: DashboardOverviewKpis = DashboardOverviewKpis(),
)

@Serializable
data class DashboardOverviewKpis(
    @SerialName("conversations_total") val conversationsTotal: Int = 0,
    @SerialName("active_conversations") val activeConversations: Int = 0,
    @SerialName("new_customers") val newCustomers: Int = 0,
    @SerialName("unread_conversations") val unreadConversations: Int = 0,
    @SerialName("takeover_on") val takeoverOn: Int = 0,
    @SerialName("campaigns_live") val campaignsLive: Int = 0,
    @SerialName("messages_in") val messagesIn: Int = 0,
    @SerialName("messages_out") val messagesOut: Int = 0,
    @SerialName("response_rate_pct") val responseRatePct: Double = 0.0,
)

@Serializable
data class DashboardFunnelResponse(
    val steps: List<DashboardFunnelStep> = emptyList(),
)

@Serializable
data class DashboardFunnelStep(
    val id: String = "",
    val label: String = "",
    val value: Int = 0,
    @SerialName("pct_prev") val pctPrev: Double = 0.0,
)

@Serializable
data class DashboardCampaignsResponse(
    @SerialName("range_days") val rangeDays: Int = 0,
    val since: String? = null,
    val metrics: DashboardCampaignMetrics = DashboardCampaignMetrics(),
)

@Serializable
data class DashboardCampaignMetrics(
    val pending: Int = 0,
    val processing: Int = 0,
    val sent: Int = 0,
    val delivered: Int = 0,
    val read: Int = 0,
    val replied: Int = 0,
    val failed: Int = 0,
    @SerialName("delivery_rate_pct") val deliveryRatePct: Double = 0.0,
    @SerialName("read_rate_pct") val readRatePct: Double = 0.0,
    @SerialName("reply_rate_pct") val replyRatePct: Double = 0.0,
)

@Serializable
data class DashboardRemarketingResponse(
    @SerialName("flows_total") val flowsTotal: Int = 0,
    @SerialName("active_flows") val activeFlows: Int = 0,
    @SerialName("steps_total") val stepsTotal: Int = 0,
)

@Serializable
data class CampaignEngineStatusResponse(
    val enabled: Boolean = false,
    val running: Boolean = false,
    @SerialName("interval_sec") val intervalSec: Int = 0,
    @SerialName("batch_size") val batchSize: Int = 0,
    @SerialName("send_delay_ms") val sendDelayMs: Int = 0,
)

@Serializable
data class RemarketingEngineStatusResponse(
    val enabled: Boolean = false,
    val running: Boolean = false,
    val runner: String = "",
    @SerialName("interval_sec") val intervalSec: Int = 0,
    @SerialName("batch_size") val batchSize: Int = 0,
    @SerialName("new_enrollments_per_flow") val newEnrollmentsPerFlow: Int = 0,
    @SerialName("resume_after_minutes") val resumeAfterMinutes: Int = 0,
    @SerialName("retry_minutes") val retryMinutes: Int = 0,
    @SerialName("service_window_hours") val serviceWindowHours: Int = 24,
    @SerialName("campaign_engine_running") val campaignEngineRunning: Boolean = false,
)

@Serializable
data class ConversationsResponse(
    val conversations: List<ConversationDto> = emptyList(),
)

@Serializable
data class ConversationDto(
    val phone: String = "",
    val takeover: Boolean = false,
    @SerialName("updated_at") val updatedAt: String? = null,
    @SerialName("first_name") val firstName: String = "",
    @SerialName("last_name") val lastName: String = "",
    val city: String = "",
    @SerialName("customer_type") val customerType: String = "",
    val interests: String = "",
    val tags: String = "",
    val notes: String = "",
    @SerialName("last_read_at") val lastReadAt: String? = null,
    @SerialName("last_text") val lastText: String = "",
    @SerialName("last_msg_type") val lastMsgType: String = "",
    @SerialName("last_direction") val lastDirection: String = "",
    @SerialName("last_channel") val lastChannel: String = "",
    @SerialName("last_created_at") val lastCreatedAt: String? = null,
    @SerialName("has_unread") val hasUnread: Boolean = false,
    @SerialName("unread_count") val unreadCount: Int = 0,
    val text: String = "",
)

@Serializable
data class MessagesResponse(
    val messages: List<MessageDto> = emptyList(),
)

@Serializable
data class MessageDto(
    val id: Long = 0,
    val phone: String = "",
    val direction: String = "",
    @SerialName("msg_type") val msgType: String = "text",
    val text: String = "",
    @SerialName("media_url") val mediaUrl: String? = null,
    @SerialName("media_caption") val mediaCaption: String? = null,
    @SerialName("media_id") val mediaId: String? = null,
    @SerialName("mime_type") val mimeType: String? = null,
    @SerialName("file_name") val fileName: String? = null,
    @SerialName("file_size") val fileSize: Long? = null,
    @SerialName("duration_sec") val durationSec: Int? = null,
    @SerialName("featured_image") val featuredImage: String? = null,
    @SerialName("real_image") val realImage: String? = null,
    val permalink: String? = null,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("wa_status") val waStatus: String? = null,
)

@Serializable
data class IngestRequest(
    val phone: String,
    val channel: String,
    val direction: String = "out",
    @SerialName("msg_type") val msgType: String = "text",
    val text: String = "",
    @SerialName("media_id") val mediaId: String? = null,
    @SerialName("media_caption") val mediaCaption: String? = null,
    @SerialName("mime_type") val mimeType: String? = null,
    @SerialName("file_name") val fileName: String? = null,
    @SerialName("file_size") val fileSize: Long? = null,
    @SerialName("duration_sec") val durationSec: Int? = null,
)

@Serializable
data class TakeoverRequest(
    val phone: String,
    val takeover: Boolean,
)

@Serializable
data class CustomersResponse(
    val page: Int = 1,
    @SerialName("page_size") val pageSize: Int = 25,
    val total: Int = 0,
    val customers: List<CustomerDto> = emptyList(),
)

@Serializable
data class CustomerEnvelope(
    val customer: CustomerDto? = null,
)

@Serializable
data class CustomerDto(
    val phone: String = "",
    val takeover: Boolean = false,
    @SerialName("updated_at") val updatedAt: String? = null,
    @SerialName("first_name") val firstName: String = "",
    @SerialName("last_name") val lastName: String = "",
    val city: String = "",
    @SerialName("customer_type") val customerType: String = "",
    val interests: String = "",
    val tags: String = "",
    val notes: String = "",
    @SerialName("intent_current") val intentCurrent: String = "",
    @SerialName("intent_stage") val intentStage: String = "",
    @SerialName("payment_status") val paymentStatus: String = "",
    @SerialName("payment_reference") val paymentReference: String = "",
    @SerialName("messages_total") val messagesTotal: Int = 0,
    @SerialName("last_text") val lastText: String = "",
    @SerialName("last_message_at") val lastMessageAt: String? = null,
    @SerialName("has_unread") val hasUnread: Boolean = false,
)

@Serializable
data class CustomerPatchRequest(
    @SerialName("first_name") val firstName: String? = null,
    @SerialName("last_name") val lastName: String? = null,
    val city: String? = null,
    @SerialName("customer_type") val customerType: String? = null,
    val interests: String? = null,
    val tags: String? = null,
    val notes: String? = null,
    @SerialName("payment_status") val paymentStatus: String? = null,
    @SerialName("payment_reference") val paymentReference: String? = null,
)

@Serializable
data class UploadMediaResponse(
    val ok: Boolean = false,
    @SerialName("media_id") val mediaId: String = "",
    @SerialName("mime_type") val mimeType: String = "",
    val filename: String = "",
    val kind: String = "",
)

@Serializable
data class WcProductsResponse(
    val products: List<WcProductDto> = emptyList(),
)

@Serializable
data class WcProductDto(
    val id: Long = 0,
    val name: String = "",
    val sku: String = "",
    val slug: String = "",
    val price: String = "",
    val permalink: String = "",
    @SerialName("featured_image") val featuredImage: String = "",
    @SerialName("real_image") val realImage: String = "",
    @SerialName("short_description") val shortDescription: String = "",
    val description: String = "",
    val brand: String = "",
    val gender: String = "",
    val size: String = "",
    @SerialName("stock_status") val stockStatus: String = "",
)

@Serializable
data class WcSendProductRequest(
    val phone: String,
    @SerialName("product_id") val productId: Long,
    val caption: String = "",
)

@Serializable
data class WcSendProductResponse(
    val ok: Boolean = false,
    val sent: Boolean = false,
)

@Serializable
data class SegmentsResponse(
    val segments: List<SegmentDto> = emptyList(),
)

@Serializable
data class SegmentDto(
    val id: Int = 0,
    val name: String = "",
    @SerialName("rules_json") val rulesJson: JsonElement? = null,
    @SerialName("is_active") val isActive: Boolean = false,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
)

@Serializable
data class TemplatesResponse(
    val templates: List<TemplateDto> = emptyList(),
)

@Serializable
data class TemplateDto(
    val id: Int = 0,
    val name: String = "",
    val category: String = "",
    val channel: String = "whatsapp",
    val body: String = "",
    @SerialName("variables_json") val variablesJson: List<String> = emptyList(),
    @SerialName("blocks_json") val blocksJson: JsonElement? = null,
    @SerialName("params_json") val paramsJson: JsonElement? = null,
    @SerialName("render_mode") val renderMode: String = "chat",
    val status: String = "draft",
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
)

@Serializable
data class TemplateEnvelope(
    val template: TemplateDto? = null,
)

@Serializable
data class TemplateCreateRequest(
    val name: String,
    val category: String = "general",
    val channel: String = "whatsapp",
    val body: String = "",
    @SerialName("render_mode") val renderMode: String = "chat",
    val status: String = "draft",
)

@Serializable
data class TemplatePatchRequest(
    val name: String? = null,
    val category: String? = null,
    val channel: String? = null,
    val body: String? = null,
    @SerialName("render_mode") val renderMode: String? = null,
    val status: String? = null,
)

@Serializable
data class CampaignsResponse(
    val campaigns: List<CampaignDto> = emptyList(),
)

@Serializable
data class CampaignDto(
    val id: Int = 0,
    val name: String = "",
    val objective: String = "",
    @SerialName("segment_id") val segmentId: Int? = null,
    @SerialName("template_id") val templateId: Int? = null,
    val status: String = "draft",
    @SerialName("scheduled_at") val scheduledAt: String? = null,
    @SerialName("launched_at") val launchedAt: String? = null,
    val channel: String = "whatsapp",
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
    @SerialName("segment_name") val segmentName: String? = null,
    @SerialName("template_name") val templateName: String? = null,
)

@Serializable
data class CampaignEnvelope(
    val campaign: CampaignDto? = null,
)

@Serializable
data class CampaignCreateRequest(
    val name: String,
    val objective: String = "",
    @SerialName("segment_id") val segmentId: Int? = null,
    @SerialName("template_id") val templateId: Int? = null,
    val status: String = "draft",
    @SerialName("scheduled_at") val scheduledAt: String? = null,
    val channel: String = "whatsapp",
)

@Serializable
data class TriggerEnvelope(
    val trigger: TriggerDto? = null,
)

@Serializable
data class TriggerCreateRequest(
    val name: String,
    val channel: String = "whatsapp",
    @SerialName("event_type") val eventType: String = "message_in",
    @SerialName("trigger_type") val triggerType: String = "message_flow",
    @SerialName("flow_event") val flowEvent: String = "received",
    @SerialName("cooldown_minutes") val cooldownMinutes: Int = 60,
    @SerialName("is_active") val isActive: Boolean = true,
    @SerialName("assistant_enabled") val assistantEnabled: Boolean = false,
    @SerialName("assistant_message_type") val assistantMessageType: String = "auto",
    val priority: Int = 100,
    @SerialName("block_ai") val blockAi: Boolean = true,
    @SerialName("stop_on_match") val stopOnMatch: Boolean = true,
    @SerialName("only_when_no_takeover") val onlyWhenNoTakeover: Boolean = true,
)

@Serializable
data class TriggerPatchRequest(
    val name: String? = null,
    val channel: String? = null,
    @SerialName("event_type") val eventType: String? = null,
    @SerialName("trigger_type") val triggerType: String? = null,
    @SerialName("flow_event") val flowEvent: String? = null,
    @SerialName("cooldown_minutes") val cooldownMinutes: Int? = null,
    @SerialName("is_active") val isActive: Boolean? = null,
    @SerialName("assistant_enabled") val assistantEnabled: Boolean? = null,
    @SerialName("assistant_message_type") val assistantMessageType: String? = null,
    val priority: Int? = null,
    @SerialName("block_ai") val blockAi: Boolean? = null,
    @SerialName("stop_on_match") val stopOnMatch: Boolean? = null,
    @SerialName("only_when_no_takeover") val onlyWhenNoTakeover: Boolean? = null,
)

@Serializable
data class TriggersResponse(
    val triggers: List<TriggerDto> = emptyList(),
)

@Serializable
data class TriggerDto(
    val id: Int = 0,
    val name: String = "",
    @SerialName("event_type") val eventType: String = "",
    @SerialName("trigger_type") val triggerType: String = "",
    @SerialName("flow_event") val flowEvent: String = "",
    val channel: String = "whatsapp",
    @SerialName("conditions_json") val conditionsJson: JsonElement? = null,
    @SerialName("action_json") val actionJson: JsonElement? = null,
    @SerialName("cooldown_minutes") val cooldownMinutes: Int = 0,
    @SerialName("is_active") val isActive: Boolean = false,
    @SerialName("last_run_at") val lastRunAt: String? = null,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
    @SerialName("assistant_enabled") val assistantEnabled: Boolean = false,
    @SerialName("assistant_message_type") val assistantMessageType: String = "text",
    val priority: Int = 100,
    @SerialName("block_ai") val blockAi: Boolean = false,
    @SerialName("stop_on_match") val stopOnMatch: Boolean = false,
    @SerialName("only_when_no_takeover") val onlyWhenNoTakeover: Boolean = false,
    @SerialName("executions_count") val executionsCount: Int = 0,
    @SerialName("last_execution_at") val lastExecutionAt: String? = null,
)

@Serializable
data class RemarketingFlowsResponse(
    val flows: List<RemarketingFlowDto> = emptyList(),
)

@Serializable
data class RemarketingFlowDto(
    val id: Int = 0,
    val name: String = "",
    val channel: String = "whatsapp",
    @SerialName("entry_rules_json") val entryRulesJson: JsonElement? = null,
    @SerialName("exit_rules_json") val exitRulesJson: JsonElement? = null,
    @SerialName("is_active") val isActive: Boolean = false,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
    @SerialName("steps_count") val stepsCount: Int = 0,
)

@Serializable
data class RemarketingFlowEnvelope(
    val flow: RemarketingFlowDto? = null,
)

@Serializable
data class RemarketingFlowCreateRequest(
    val name: String,
    val channel: String = "whatsapp",
    @SerialName("is_active") val isActive: Boolean = false,
)

@Serializable
data class RemarketingFlowPatchRequest(
    val name: String? = null,
    val channel: String? = null,
    @SerialName("is_active") val isActive: Boolean? = null,
)

@Serializable
data class RemarketingStepsResponse(
    val steps: List<RemarketingStepDto> = emptyList(),
)

@Serializable
data class RemarketingStepDto(
    val id: Int = 0,
    @SerialName("flow_id") val flowId: Int = 0,
    @SerialName("step_order") val stepOrder: Int = 1,
    @SerialName("stage_name") val stageName: String = "",
    @SerialName("wait_minutes") val waitMinutes: Int = 0,
    @SerialName("template_id") val templateId: Int? = null,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("template_name") val templateName: String? = null,
)

@Serializable
data class RemarketingStepEnvelope(
    val step: RemarketingStepDto? = null,
)

@Serializable
data class RemarketingStepCreateRequest(
    @SerialName("step_order") val stepOrder: Int = 1,
    @SerialName("stage_name") val stageName: String = "",
    @SerialName("wait_minutes") val waitMinutes: Int = 1440,
    @SerialName("template_id") val templateId: Int? = null,
)

@Serializable
data class RemarketingStepPatchRequest(
    @SerialName("step_order") val stepOrder: Int? = null,
    @SerialName("stage_name") val stageName: String? = null,
    @SerialName("wait_minutes") val waitMinutes: Int? = null,
    @SerialName("template_id") val templateId: Int? = null,
)

@Serializable
data class RemarketingEnrollmentsResponse(
    val enrollments: List<RemarketingEnrollmentDto> = emptyList(),
)

@Serializable
data class RemarketingEnrollmentDto(
    val id: Int = 0,
    @SerialName("flow_id") val flowId: Int = 0,
    val phone: String = "",
    @SerialName("current_step_order") val currentStepOrder: Int = 0,
    val state: String = "",
    @SerialName("enrolled_at") val enrolledAt: String? = null,
    @SerialName("step_started_at") val stepStartedAt: String? = null,
    @SerialName("next_run_at") val nextRunAt: String? = null,
    @SerialName("last_sent_at") val lastSentAt: String? = null,
    @SerialName("last_sent_step_order") val lastSentStepOrder: Int? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
    @SerialName("meta_json") val metaJson: JsonElement? = null,
    @SerialName("first_name") val firstName: String = "",
    @SerialName("last_name") val lastName: String = "",
    val tags: String = "",
    @SerialName("current_stage_name") val currentStageName: String? = null,
    @SerialName("current_template_id") val currentTemplateId: Int? = null,
    @SerialName("current_template_name") val currentTemplateName: String? = null,
)

@Serializable
data class RemarketingDispatchRequest(
    val limit: Int = 600,
    @SerialName("include_hold") val includeHold: Boolean = false,
)

@Serializable
data class SecurityAuthModeResponse(
    val enabled: Boolean = false,
    @SerialName("open_mode") val openMode: Boolean = true,
    @SerialName("configured_roles") val configuredRoles: List<String> = emptyList(),
)

@Serializable
data class SecurityStateResponse(
    val policy: SecurityPolicyDto = SecurityPolicyDto(),
    val mfa: SecurityMfaDto = SecurityMfaDto(),
    val alerts: SecurityAlertsDto = SecurityAlertsDto(),
    val users: List<SecurityUserDto> = emptyList(),
    val sessions: List<SecuritySessionDto> = emptyList(),
    val keys: List<SecurityApiKeyDto> = emptyList(),
    @SerialName("audit_events") val auditEvents: List<SecurityAuditEventDto> = emptyList(),
    val summary: SecuritySummaryDto = SecuritySummaryDto(),
)

@Serializable
data class SecurityPolicyDto(
    @SerialName("password_min_length") val passwordMinLength: Int = 10,
    @SerialName("require_special_chars") val requireSpecialChars: Boolean = false,
    @SerialName("access_token_minutes") val accessTokenMinutes: Int = 30,
    @SerialName("refresh_token_days") val refreshTokenDays: Int = 7,
    @SerialName("session_idle_minutes") val sessionIdleMinutes: Int = 30,
    @SerialName("session_absolute_hours") val sessionAbsoluteHours: Int = 12,
    @SerialName("max_failed_attempts") val maxFailedAttempts: Int = 5,
    @SerialName("lock_minutes") val lockMinutes: Int = 20,
    @SerialName("force_password_rotation_days") val forcePasswordRotationDays: Int = 90,
    @SerialName("updated_at") val updatedAt: String? = null,
)

@Serializable
data class SecurityMfaDto(
    @SerialName("enforce_for_admins") val enforceForAdmins: Boolean = true,
    @SerialName("enforce_for_supervisors") val enforceForSupervisors: Boolean = true,
    @SerialName("allow_for_agents") val allowForAgents: Boolean = true,
    @SerialName("backup_codes_enabled") val backupCodesEnabled: Boolean = true,
    @SerialName("updated_at") val updatedAt: String? = null,
)

@Serializable
data class SecurityAlertsDto(
    @SerialName("failed_login_alert") val failedLoginAlert: Boolean = true,
    @SerialName("suspicious_ip_alert") val suspiciousIpAlert: Boolean = true,
    @SerialName("security_change_alert") val securityChangeAlert: Boolean = true,
    @SerialName("webhook_failure_alert") val webhookFailureAlert: Boolean = false,
    @SerialName("channel_email") val channelEmail: Boolean = true,
    @SerialName("channel_whatsapp") val channelWhatsapp: Boolean = true,
    @SerialName("updated_at") val updatedAt: String? = null,
)

@Serializable
data class SecuritySummaryDto(
    @SerialName("active_users") val activeUsers: Int = 0,
    @SerialName("users_with_2fa") val usersWith2fa: Int = 0,
    @SerialName("total_users") val totalUsers: Int = 0,
    @SerialName("open_sessions") val openSessions: Int = 0,
    @SerialName("critical_events_24h") val criticalEvents24h: Int = 0,
)

@Serializable
data class SecurityUserDto(
    val id: Int = 0,
    val name: String = "",
    val email: String = "",
    val role: String = "agente",
    val twofa: Boolean = false,
    val active: Boolean = true,
    @SerialName("last_login") val lastLogin: String? = null,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
)

@Serializable
data class SecuritySessionDto(
    val id: String = "",
    @SerialName("user") val userName: String = "",
    val device: String = "",
    val ip: String = "",
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("last_seen") val lastSeen: String? = null,
)

@Serializable
data class SecurityApiKeyDto(
    val id: Int = 0,
    val name: String = "",
    val scope: String = "",
    val value: String = "",
    @SerialName("is_active") val isActive: Boolean = true,
    @SerialName("rotation_days") val rotationDays: Int = 90,
    @SerialName("next_rotation_at") val nextRotationAt: String? = null,
    @SerialName("last_rotated_at") val lastRotatedAt: String? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
    @SerialName("created_at") val createdAt: String? = null,
)

@Serializable
data class SecurityAuditEventDto(
    val id: Int = 0,
    val level: String = "",
    val action: String = "",
    val actor: String = "",
    val ip: String = "",
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("details_json") val detailsJson: JsonElement? = null,
)

@Serializable
data class SecurityRotationStatusResponse(
    val enabled: Boolean = false,
    val running: Boolean = false,
    @SerialName("interval_sec") val intervalSec: Int = 0,
)

@Serializable
data class SecurityRotationTickResponse(
    val ok: Boolean = false,
    val scanned: Int = 0,
    val rotated: Int = 0,
    val errors: List<String> = emptyList(),
)

@Serializable
data class SecurityPolicyPatchRequest(
    @SerialName("password_min_length") val passwordMinLength: Int? = null,
    @SerialName("require_special_chars") val requireSpecialChars: Boolean? = null,
    @SerialName("access_token_minutes") val accessTokenMinutes: Int? = null,
    @SerialName("refresh_token_days") val refreshTokenDays: Int? = null,
    @SerialName("session_idle_minutes") val sessionIdleMinutes: Int? = null,
    @SerialName("session_absolute_hours") val sessionAbsoluteHours: Int? = null,
    @SerialName("max_failed_attempts") val maxFailedAttempts: Int? = null,
    @SerialName("lock_minutes") val lockMinutes: Int? = null,
    @SerialName("force_password_rotation_days") val forcePasswordRotationDays: Int? = null,
)

@Serializable
data class SecurityMfaPatchRequest(
    @SerialName("enforce_for_admins") val enforceForAdmins: Boolean? = null,
    @SerialName("enforce_for_supervisors") val enforceForSupervisors: Boolean? = null,
    @SerialName("allow_for_agents") val allowForAgents: Boolean? = null,
    @SerialName("backup_codes_enabled") val backupCodesEnabled: Boolean? = null,
)

@Serializable
data class SecurityAlertsPatchRequest(
    @SerialName("failed_login_alert") val failedLoginAlert: Boolean? = null,
    @SerialName("suspicious_ip_alert") val suspiciousIpAlert: Boolean? = null,
    @SerialName("security_change_alert") val securityChangeAlert: Boolean? = null,
    @SerialName("webhook_failure_alert") val webhookFailureAlert: Boolean? = null,
    @SerialName("channel_email") val channelEmail: Boolean? = null,
    @SerialName("channel_whatsapp") val channelWhatsapp: Boolean? = null,
)

@Serializable
data class SecurityUserCreateRequest(
    val name: String,
    val email: String,
    val role: String = "agente",
    val twofa: Boolean = false,
    val active: Boolean = true,
    val password: String? = null,
)

@Serializable
data class SecurityUserPatchRequest(
    val name: String? = null,
    val email: String? = null,
    val role: String? = null,
    val twofa: Boolean? = null,
    val active: Boolean? = null,
)

@Serializable
data class SecurityUserEnvelopeResponse(
    val ok: Boolean = false,
    val user: SecurityUserDto? = null,
    @SerialName("temp_password") val tempPassword: String? = null,
    @SerialName("twofa_pending_setup") val twofaPendingSetup: Boolean? = null,
    @SerialName("twofa_setup_secret") val twofaSetupSecret: String? = null,
    @SerialName("twofa_setup_uri") val twofaSetupUri: String? = null,
)

@Serializable
data class SecurityPasswordResetRequest(
    val password: String? = null,
)

@Serializable
data class SecurityPasswordResetResponse(
    val ok: Boolean = false,
    @SerialName("user_id") val userId: Int = 0,
    @SerialName("temp_password") val tempPassword: String = "",
)

@Serializable
data class SecurityTwofaSetupResponse(
    val ok: Boolean = false,
    @SerialName("user_id") val userId: Int = 0,
    val secret: String = "",
    @SerialName("otpauth_uri") val otpauthUri: String = "",
)

@Serializable
data class SecurityTwofaVerifyRequest(
    val code: String,
)

@Serializable
data class SecurityTwofaVerifyResponse(
    val ok: Boolean = false,
    @SerialName("user_id") val userId: Int = 0,
    val twofa: Boolean = false,
)

@Serializable
data class SecuritySessionRevokeResponse(
    val ok: Boolean = false,
    @SerialName("session_id") val sessionId: String = "",
    val revoked: Boolean = false,
)

@Serializable
data class SecurityRevokeAllResponse(
    val ok: Boolean = false,
    @SerialName("revoked_count") val revokedCount: Int = 0,
)

@Serializable
data class SecurityKeyCreateRequest(
    val name: String,
    val scope: String = "general",
    @SerialName("rotation_days") val rotationDays: Int = 90,
)

@Serializable
data class SecurityKeyPatchRequest(
    val name: String? = null,
    val scope: String? = null,
    @SerialName("is_active") val isActive: Boolean? = null,
    @SerialName("rotation_days") val rotationDays: Int? = null,
)

@Serializable
data class SecurityKeyEnvelopeResponse(
    val ok: Boolean = false,
    val key: SecurityApiKeyDto? = null,
    @SerialName("plain_secret") val plainSecret: String? = null,
)

@Serializable
data class SecurityRevealKeyResponse(
    val ok: Boolean = false,
    @SerialName("key_id") val keyId: Int = 0,
    @SerialName("plain_secret") val plainSecret: String = "",
)

@Serializable
data class SecurityAuditResponse(
    val events: List<SecurityAuditEventDto> = emptyList(),
)

@Serializable
data class SecurityPatchResultResponse(
    val ok: Boolean = false,
    val policy: SecurityPolicyDto? = null,
    val mfa: SecurityMfaDto? = null,
    val alerts: SecurityAlertsDto? = null,
    val summary: SecuritySummaryDto? = null,
)

@Serializable
data class MobilePushRegisterRequest(
    val token: String,
    val platform: String = "android",
    @SerialName("app_version") val appVersion: String = "",
    @SerialName("device_id") val deviceId: String = "",
    val role: String = "agente",
    val actor: String = "",
    @SerialName("notifications_enabled") val notificationsEnabled: Boolean = true,
)

@Serializable
data class MobilePushRegisterResponse(
    val ok: Boolean = false,
    val registered: Boolean = false,
    val role: String = "",
)

@Serializable
data class MobilePushUnregisterRequest(
    val token: String,
)

@Serializable
data class MobilePushUnregisterResponse(
    val ok: Boolean = false,
    val unregistered: Int = 0,
)

@Serializable
data class MobilePushStateResponse(
    val summary: JsonObject = JsonObject(emptyMap()),
    val events: List<JsonObject> = emptyList(),
)

@Serializable
data class MobilePushTestRequest(
    val title: String = "Prueba push Verane",
    val body: String = "Push de prueba enviado desde backend",
    @SerialName("event_type") val eventType: String = "manual_test",
    @SerialName("role_scope") val roleScope: String = "all",
    val data: JsonObject = JsonObject(emptyMap()),
)

@Serializable
data class MobilePushTestResponse(
    val ok: Boolean = false,
    val result: JsonObject = JsonObject(emptyMap()),
)

@Serializable
data class AiSettingsDto(
    val id: Int = 0,
    @SerialName("is_enabled") val isEnabled: Boolean = true,
    val provider: String = "google",
    val model: String = "",
    @SerialName("system_prompt") val systemPrompt: String = "",
    @SerialName("max_tokens") val maxTokens: Int = 512,
    val temperature: Double = 0.7,
    @SerialName("fallback_provider") val fallbackProvider: String = "",
    @SerialName("fallback_model") val fallbackModel: String = "",
    @SerialName("timeout_sec") val timeoutSec: Int = 25,
    @SerialName("max_retries") val maxRetries: Int = 1,
    @SerialName("reply_chunk_chars") val replyChunkChars: Int = 480,
    @SerialName("reply_delay_ms") val replyDelayMs: Int = 900,
    @SerialName("typing_delay_ms") val typingDelayMs: Int = 450,
    @SerialName("inbound_cooldown_sec") val inboundCooldownSec: Int = 6,
    @SerialName("inbound_post_activity_ms") val inboundPostActivityMs: Int = 1400,
    @SerialName("inbound_audio_extra_ms") val inboundAudioExtraMs: Int = 2500,
    @SerialName("voice_enabled") val voiceEnabled: Boolean = false,
    @SerialName("voice_gender") val voiceGender: String = "neutral",
    @SerialName("voice_language") val voiceLanguage: String = "es-CO",
    @SerialName("voice_accent") val voiceAccent: String = "colombiano",
    @SerialName("voice_style_prompt") val voiceStylePrompt: String = "",
    @SerialName("voice_max_notes_per_reply") val voiceMaxNotesPerReply: Int = 1,
    @SerialName("voice_prefer_voice") val voicePreferVoice: Boolean = false,
    @SerialName("voice_speaking_rate") val voiceSpeakingRate: Double = 1.0,
    @SerialName("voice_tts_provider") val voiceTtsProvider: String = "google",
    @SerialName("voice_tts_voice_id") val voiceTtsVoiceId: String = "",
    @SerialName("voice_tts_model_id") val voiceTtsModelId: String = "",
    @SerialName("mm_enabled") val mmEnabled: Boolean = true,
    @SerialName("mm_provider") val mmProvider: String = "google",
    @SerialName("mm_model") val mmModel: String = "gemini-2.5-flash",
    @SerialName("mm_timeout_sec") val mmTimeoutSec: Int = 75,
    @SerialName("mm_max_retries") val mmMaxRetries: Int = 2,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
)

@Serializable
data class AiSettingsUpdateRequest(
    @SerialName("is_enabled") val isEnabled: Boolean? = null,
    val provider: String? = null,
    val model: String? = null,
    @SerialName("system_prompt") val systemPrompt: String? = null,
    @SerialName("max_tokens") val maxTokens: Int? = null,
    val temperature: Double? = null,
    @SerialName("fallback_provider") val fallbackProvider: String? = null,
    @SerialName("fallback_model") val fallbackModel: String? = null,
    @SerialName("timeout_sec") val timeoutSec: Int? = null,
    @SerialName("max_retries") val maxRetries: Int? = null,
    @SerialName("reply_chunk_chars") val replyChunkChars: Int? = null,
    @SerialName("reply_delay_ms") val replyDelayMs: Int? = null,
    @SerialName("typing_delay_ms") val typingDelayMs: Int? = null,
    @SerialName("inbound_cooldown_sec") val inboundCooldownSec: Int? = null,
    @SerialName("inbound_post_activity_ms") val inboundPostActivityMs: Int? = null,
    @SerialName("inbound_audio_extra_ms") val inboundAudioExtraMs: Int? = null,
    @SerialName("voice_enabled") val voiceEnabled: Boolean? = null,
    @SerialName("voice_gender") val voiceGender: String? = null,
    @SerialName("voice_language") val voiceLanguage: String? = null,
    @SerialName("voice_accent") val voiceAccent: String? = null,
    @SerialName("voice_style_prompt") val voiceStylePrompt: String? = null,
    @SerialName("voice_max_notes_per_reply") val voiceMaxNotesPerReply: Int? = null,
    @SerialName("voice_prefer_voice") val voicePreferVoice: Boolean? = null,
    @SerialName("voice_speaking_rate") val voiceSpeakingRate: Double? = null,
    @SerialName("voice_tts_provider") val voiceTtsProvider: String? = null,
    @SerialName("voice_tts_voice_id") val voiceTtsVoiceId: String? = null,
    @SerialName("voice_tts_model_id") val voiceTtsModelId: String? = null,
    @SerialName("mm_enabled") val mmEnabled: Boolean? = null,
    @SerialName("mm_provider") val mmProvider: String? = null,
    @SerialName("mm_model") val mmModel: String? = null,
    @SerialName("mm_timeout_sec") val mmTimeoutSec: Int? = null,
    @SerialName("mm_max_retries") val mmMaxRetries: Int? = null,
)

@Serializable
data class AiModelsCatalogResponse(
    val providers: JsonObject = JsonObject(emptyMap()),
    val tts: JsonObject = JsonObject(emptyMap()),
    val mm: JsonObject = JsonObject(emptyMap()),
    val defaults: JsonObject = JsonObject(emptyMap()),
)

@Serializable
data class AiProcessRequest(
    val phone: String,
    val text: String = "",
)

@Serializable
data class AiProcessResponse(
    val ok: Boolean = false,
    val provider: String = "",
    val model: String = "",
    @SerialName("reply_text") val replyText: String = "",
    @SerialName("used_fallback") val usedFallback: Boolean = false,
    val error: String? = null,
)

@Serializable
data class AiTtsRequest(
    val text: String,
    val provider: String? = null,
    @SerialName("voice_id") val voiceId: String? = null,
    @SerialName("model_id") val modelId: String? = null,
)

@Serializable
data class KnowledgeFilesResponse(
    val files: List<KnowledgeFileDto> = emptyList(),
)

@Serializable
data class KnowledgeFileDto(
    val id: String = "",
    @SerialName("file_name") val fileName: String = "",
    @SerialName("mime_type") val mimeType: String = "",
    @SerialName("size_bytes") val sizeBytes: Long = 0,
    val notes: String = "",
    @SerialName("is_active") val isActive: Boolean = true,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
)

@Serializable
data class KnowledgeUploadResponse(
    val id: String = "",
    @SerialName("file_name") val fileName: String = "",
    @SerialName("mime_type") val mimeType: String = "",
    @SerialName("size_bytes") val sizeBytes: Long = 0,
    val notes: String = "",
    @SerialName("is_active") val isActive: Boolean = true,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
)

@Serializable
data class KnowledgeWebSourceCreateRequest(
    val url: String,
    @SerialName("source_name") val sourceName: String = "",
    val notes: String = "",
    @SerialName("is_active") val isActive: Boolean = true,
    @SerialName("auto_sync") val autoSync: Boolean = true,
    @SerialName("sync_interval_min") val syncIntervalMin: Int = 360,
    @SerialName("timeout_sec") val timeoutSec: Int = 20,
)

@Serializable
data class KnowledgeWebSourcePatchRequest(
    val url: String? = null,
    @SerialName("source_name") val sourceName: String? = null,
    val notes: String? = null,
    @SerialName("is_active") val isActive: Boolean? = null,
    @SerialName("auto_sync") val autoSync: Boolean? = null,
    @SerialName("sync_interval_min") val syncIntervalMin: Int? = null,
    @SerialName("timeout_sec") val timeoutSec: Int? = null,
)

@Serializable
data class KnowledgeWebSourceDto(
    val id: String = "",
    val url: String = "",
    @SerialName("source_name") val sourceName: String = "",
    val notes: String = "",
    @SerialName("is_active") val isActive: Boolean = true,
    @SerialName("auto_sync") val autoSync: Boolean = true,
    @SerialName("sync_interval_min") val syncIntervalMin: Int = 360,
    @SerialName("timeout_sec") val timeoutSec: Int = 20,
    @SerialName("file_id") val fileId: String = "",
    @SerialName("last_synced_at") val lastSyncedAt: String? = null,
    @SerialName("last_status") val lastStatus: String = "",
    @SerialName("last_error") val lastError: String = "",
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
)

@Serializable
data class KnowledgeSyncResultResponse(
    val ok: Boolean = false,
    @SerialName("source_id") val sourceId: String? = null,
    @SerialName("file_id") val fileId: String? = null,
    val url: String? = null,
    val chunks: Int? = null,
    @SerialName("size_bytes") val sizeBytes: Long? = null,
    val error: String? = null,
)

@Serializable
data class KnowledgeSyncDueResponse(
    val ok: Boolean = false,
    val checked: Int = 0,
    val due: Int = 0,
    val synced: Int = 0,
    val failed: Int = 0,
    val results: List<KnowledgeSyncResultResponse> = emptyList(),
)
