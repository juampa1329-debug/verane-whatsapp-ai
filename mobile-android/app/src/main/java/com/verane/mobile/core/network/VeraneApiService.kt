package com.verane.mobile.core.network

import kotlinx.serialization.json.JsonObject
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.ResponseBody
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.PUT
import retrofit2.http.Query

interface VeraneApiService {
    @GET("api/dashboard/overview")
    suspend fun getDashboardOverview(
        @Query("range") range: String = "7d",
    ): DashboardOverviewResponse

    @GET("api/dashboard/funnel")
    suspend fun getDashboardFunnel(): DashboardFunnelResponse

    @GET("api/dashboard/campaigns")
    suspend fun getDashboardCampaigns(
        @Query("range") range: String = "30d",
    ): DashboardCampaignsResponse

    @GET("api/dashboard/remarketing")
    suspend fun getDashboardRemarketing(): DashboardRemarketingResponse

    @GET("api/campaigns/engine/status")
    suspend fun getCampaignEngineStatus(): CampaignEngineStatusResponse

    @POST("api/campaigns/engine/tick")
    suspend fun tickCampaignEngine(
        @Query("batch_size") batchSize: Int = 20,
        @Query("send_delay_ms") sendDelayMs: Int = 0,
    ): JsonObject

    @GET("api/remarketing/engine/status")
    suspend fun getRemarketingEngineStatus(): RemarketingEngineStatusResponse

    @POST("api/remarketing/engine/tick")
    suspend fun tickRemarketingEngine(
        @Query("limit") limit: Int = 300,
        @Query("flow_id") flowId: Int = 0,
        @Query("channel") channel: String = "all",
    ): JsonObject

    @GET("api/conversations")
    suspend fun getConversations(
        @Query("search") search: String = "",
        @Query("takeover") takeover: String = "all",
        @Query("unread") unread: String = "all",
        @Query("tags") tags: String = "",
        @Query("channel") channel: String = "all",
    ): ConversationsResponse

    @GET("api/conversations/{phone}/messages")
    suspend fun getMessages(
        @Path(value = "phone", encoded = true) phone: String,
        @Query("channel") channel: String = "all",
    ): MessagesResponse

    @POST("api/conversations/{phone}/read")
    suspend fun markConversationRead(
        @Path(value = "phone", encoded = true) phone: String,
    ): ApiOkResponse

    @POST("api/messages/ingest")
    suspend fun ingestMessage(
        @Body request: IngestRequest,
    ): JsonObject

    @POST("api/conversations/takeover")
    suspend fun setTakeover(
        @Body request: TakeoverRequest,
    ): ApiOkResponse

    @GET("api/customers")
    suspend fun getCustomers(
        @Query("search") search: String = "",
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 50,
    ): CustomersResponse

    @GET("api/customers/{phone}")
    suspend fun getCustomer(
        @Path(value = "phone", encoded = true) phone: String,
    ): CustomerEnvelope

    @PATCH("api/customers/{phone}")
    suspend fun patchCustomer(
        @Path(value = "phone", encoded = true) phone: String,
        @Body body: CustomerPatchRequest,
    ): CustomerEnvelope

    @GET("api/customers/segments")
    suspend fun getSegments(
        @Query("active") active: String = "all",
    ): SegmentsResponse

    @GET("api/templates")
    suspend fun getTemplates(
        @Query("status") status: String = "all",
        @Query("channel") channel: String = "all",
        @Query("category") category: String = "",
        @Query("search") search: String = "",
    ): TemplatesResponse

    @POST("api/templates")
    suspend fun createTemplate(
        @Body request: TemplateCreateRequest,
    ): TemplateEnvelope

    @PATCH("api/templates/{template_id}")
    suspend fun patchTemplate(
        @Path("template_id") templateId: Int,
        @Body request: TemplatePatchRequest,
    ): TemplateEnvelope

    @DELETE("api/templates/{template_id}")
    suspend fun deleteTemplate(
        @Path("template_id") templateId: Int,
    ): JsonObject

    @GET("api/campaigns")
    suspend fun getCampaigns(
        @Query("status") status: String = "all",
        @Query("channel") channel: String = "all",
    ): CampaignsResponse

    @POST("api/campaigns")
    suspend fun createCampaign(
        @Body request: CampaignCreateRequest,
    ): CampaignEnvelope

    @DELETE("api/campaigns/{campaign_id}")
    suspend fun deleteCampaign(
        @Path("campaign_id") campaignId: Int,
    ): JsonObject

    @POST("api/campaigns/{campaign_id}/launch")
    suspend fun launchCampaign(
        @Path("campaign_id") campaignId: Int,
        @Query("max_recipients") maxRecipients: Int = 300,
    ): JsonObject

    @GET("api/triggers")
    suspend fun getTriggers(
        @Query("active") active: String = "all",
        @Query("channel") channel: String = "all",
    ): TriggersResponse

    @POST("api/triggers")
    suspend fun createTrigger(
        @Body request: TriggerCreateRequest,
    ): TriggerEnvelope

    @PATCH("api/triggers/{trigger_id}")
    suspend fun patchTrigger(
        @Path("trigger_id") triggerId: Int,
        @Body request: TriggerPatchRequest,
    ): TriggerEnvelope

    @DELETE("api/triggers/{trigger_id}")
    suspend fun deleteTrigger(
        @Path("trigger_id") triggerId: Int,
    ): JsonObject

    @GET("api/remarketing/flows")
    suspend fun getRemarketingFlows(
        @Query("channel") channel: String = "all",
    ): RemarketingFlowsResponse

    @POST("api/remarketing/flows")
    suspend fun createRemarketingFlow(
        @Body request: RemarketingFlowCreateRequest,
    ): RemarketingFlowEnvelope

    @PATCH("api/remarketing/flows/{flow_id}")
    suspend fun patchRemarketingFlow(
        @Path("flow_id") flowId: Int,
        @Body request: RemarketingFlowPatchRequest,
    ): RemarketingFlowEnvelope

    @DELETE("api/remarketing/flows/{flow_id}")
    suspend fun deleteRemarketingFlow(
        @Path("flow_id") flowId: Int,
    ): JsonObject

    @GET("api/remarketing/flows/{flow_id}/steps")
    suspend fun getRemarketingFlowSteps(
        @Path("flow_id") flowId: Int,
    ): RemarketingStepsResponse

    @POST("api/remarketing/flows/{flow_id}/steps")
    suspend fun createRemarketingStep(
        @Path("flow_id") flowId: Int,
        @Body request: RemarketingStepCreateRequest,
    ): RemarketingStepEnvelope

    @PATCH("api/remarketing/steps/{step_id}")
    suspend fun patchRemarketingStep(
        @Path("step_id") stepId: Int,
        @Body request: RemarketingStepPatchRequest,
    ): RemarketingStepEnvelope

    @DELETE("api/remarketing/steps/{step_id}")
    suspend fun deleteRemarketingStep(
        @Path("step_id") stepId: Int,
    ): JsonObject

    @GET("api/remarketing/flows/{flow_id}/enrollments")
    suspend fun getRemarketingEnrollments(
        @Path("flow_id") flowId: Int,
        @Query("state") state: String = "all",
        @Query("limit") limit: Int = 120,
    ): RemarketingEnrollmentsResponse

    @POST("api/remarketing/flows/{flow_id}/dispatch")
    suspend fun dispatchRemarketingFlow(
        @Path("flow_id") flowId: Int,
        @Body request: RemarketingDispatchRequest,
    ): JsonObject

    @POST("api/remarketing/steps/{step_id}/dispatch")
    suspend fun dispatchRemarketingStep(
        @Path("step_id") stepId: Int,
        @Body request: RemarketingDispatchRequest,
    ): JsonObject

    @GET("api/security/auth/mode")
    suspend fun getSecurityAuthMode(): SecurityAuthModeResponse

    @GET("api/security/state")
    suspend fun getSecurityState(
        @Query("audit_level") auditLevel: String = "all",
        @Query("audit_limit") auditLimit: Int = 50,
    ): SecurityStateResponse

    @GET("api/security/rotation/status")
    suspend fun getSecurityRotationStatus(): SecurityRotationStatusResponse

    @POST("api/security/rotation/tick")
    suspend fun tickSecurityRotation(
        @Query("limit") limit: Int = 60,
    ): SecurityRotationTickResponse

    @PUT("api/security/policy")
    suspend fun updateSecurityPolicy(
        @Body request: SecurityPolicyPatchRequest,
    ): SecurityPatchResultResponse

    @PUT("api/security/mfa")
    suspend fun updateSecurityMfa(
        @Body request: SecurityMfaPatchRequest,
    ): SecurityPatchResultResponse

    @PUT("api/security/alerts")
    suspend fun updateSecurityAlerts(
        @Body request: SecurityAlertsPatchRequest,
    ): SecurityPatchResultResponse

    @POST("api/security/users")
    suspend fun createSecurityUser(
        @Body request: SecurityUserCreateRequest,
    ): SecurityUserEnvelopeResponse

    @PATCH("api/security/users/{user_id}")
    suspend fun patchSecurityUser(
        @Path("user_id") userId: Int,
        @Body request: SecurityUserPatchRequest,
    ): SecurityUserEnvelopeResponse

    @POST("api/security/users/{user_id}/password/reset")
    suspend fun resetSecurityUserPassword(
        @Path("user_id") userId: Int,
        @Body request: SecurityPasswordResetRequest,
    ): SecurityPasswordResetResponse

    @POST("api/security/users/{user_id}/2fa/setup")
    suspend fun setupSecurityUser2fa(
        @Path("user_id") userId: Int,
    ): SecurityTwofaSetupResponse

    @POST("api/security/users/{user_id}/2fa/verify")
    suspend fun verifySecurityUser2fa(
        @Path("user_id") userId: Int,
        @Body request: SecurityTwofaVerifyRequest,
    ): SecurityTwofaVerifyResponse

    @POST("api/security/users/{user_id}/2fa/disable")
    suspend fun disableSecurityUser2fa(
        @Path("user_id") userId: Int,
    ): SecurityTwofaVerifyResponse

    @POST("api/security/sessions/{session_id}/revoke")
    suspend fun revokeSecuritySession(
        @Path("session_id") sessionId: String,
    ): SecuritySessionRevokeResponse

    @POST("api/security/sessions/revoke-all")
    suspend fun revokeAllSecuritySessions(): SecurityRevokeAllResponse

    @POST("api/security/keys")
    suspend fun createSecurityKey(
        @Body request: SecurityKeyCreateRequest,
    ): SecurityKeyEnvelopeResponse

    @POST("api/security/keys/{key_id}/rotate")
    suspend fun rotateSecurityKey(
        @Path("key_id") keyId: Int,
    ): SecurityKeyEnvelopeResponse

    @PATCH("api/security/keys/{key_id}")
    suspend fun patchSecurityKey(
        @Path("key_id") keyId: Int,
        @Body request: SecurityKeyPatchRequest,
    ): SecurityKeyEnvelopeResponse

    @POST("api/security/keys/{key_id}/reveal")
    suspend fun revealSecurityKey(
        @Path("key_id") keyId: Int,
    ): SecurityRevealKeyResponse

    @GET("api/security/audit")
    suspend fun getSecurityAudit(
        @Query("level") level: String = "all",
        @Query("limit") limit: Int = 120,
    ): SecurityAuditResponse

    @POST("api/mobile/push/register")
    suspend fun registerMobilePushToken(
        @Body request: MobilePushRegisterRequest,
    ): MobilePushRegisterResponse

    @POST("api/push/register")
    suspend fun registerMobilePushTokenCompat(
        @Body request: MobilePushRegisterRequest,
    ): MobilePushRegisterResponse

    @POST("api/mobile/push/unregister")
    suspend fun unregisterMobilePushToken(
        @Body request: MobilePushUnregisterRequest,
    ): MobilePushUnregisterResponse

    @POST("api/push/unregister")
    suspend fun unregisterMobilePushTokenCompat(
        @Body request: MobilePushUnregisterRequest,
    ): MobilePushUnregisterResponse

    @GET("api/mobile/push/state")
    suspend fun getMobilePushState(): MobilePushStateResponse

    @GET("api/push/state")
    suspend fun getMobilePushStateCompat(): MobilePushStateResponse

    @POST("api/mobile/push/test")
    suspend fun testMobilePush(
        @Body request: MobilePushTestRequest,
    ): MobilePushTestResponse

    @POST("api/push/test")
    suspend fun testMobilePushCompat(
        @Body request: MobilePushTestRequest,
    ): MobilePushTestResponse

    @GET("api/wc/products")
    suspend fun getWcProducts(
        @Query("q") q: String = "",
        @Query("page") page: Int = 1,
        @Query("per_page") perPage: Int = 12,
    ): WcProductsResponse

    @POST("api/wc/send-product")
    suspend fun sendWcProduct(
        @Body request: WcSendProductRequest,
    ): WcSendProductResponse

    @GET("api/ai/settings")
    suspend fun getAiSettings(): AiSettingsDto

    @PUT("api/ai/settings")
    suspend fun updateAiSettings(
        @Body request: AiSettingsUpdateRequest,
    ): AiSettingsDto

    @GET("api/ai/models")
    suspend fun getAiModelsCatalog(): AiModelsCatalogResponse

    @POST("api/ai/process-message")
    suspend fun processAiMessage(
        @Body request: AiProcessRequest,
    ): AiProcessResponse

    @GET("api/ai/knowledge/files")
    suspend fun getKnowledgeFiles(
        @Query("active") active: String = "all",
        @Query("limit") limit: Int = 200,
    ): List<KnowledgeFileDto>

    @Multipart
    @POST("api/ai/knowledge/upload")
    suspend fun uploadKnowledgeFile(
        @Part file: MultipartBody.Part,
        @Part("notes") notes: RequestBody,
    ): KnowledgeUploadResponse

    @DELETE("api/ai/knowledge/files/{file_id}")
    suspend fun deleteKnowledgeFile(
        @Path("file_id") fileId: String,
    ): ApiOkResponse

    @POST("api/ai/knowledge/reindex/{file_id}")
    suspend fun reindexKnowledgeFile(
        @Path("file_id") fileId: String,
    ): JsonObject

    @GET("api/ai/knowledge/web-sources")
    suspend fun getKnowledgeWebSources(
        @Query("active") active: String = "all",
        @Query("limit") limit: Int = 200,
    ): List<KnowledgeWebSourceDto>

    @POST("api/ai/knowledge/web-sources")
    suspend fun createKnowledgeWebSource(
        @Body request: KnowledgeWebSourceCreateRequest,
    ): KnowledgeWebSourceDto

    @PUT("api/ai/knowledge/web-sources/{source_id}")
    suspend fun updateKnowledgeWebSource(
        @Path("source_id") sourceId: String,
        @Body request: KnowledgeWebSourcePatchRequest,
    ): KnowledgeWebSourceDto

    @DELETE("api/ai/knowledge/web-sources/{source_id}")
    suspend fun deleteKnowledgeWebSource(
        @Path("source_id") sourceId: String,
    ): ApiOkResponse

    @POST("api/ai/knowledge/web-sources/{source_id}/sync")
    suspend fun syncKnowledgeWebSource(
        @Path("source_id") sourceId: String,
    ): KnowledgeSyncResultResponse

    @POST("api/ai/knowledge/web-sources/sync-due")
    suspend fun syncDueKnowledgeWebSources(
        @Query("limit") limit: Int = 10,
    ): KnowledgeSyncDueResponse

    @POST("api/ai/tts")
    suspend fun testAiTts(
        @Body request: AiTtsRequest,
    ): ResponseBody

    @Multipart
    @POST("api/media/upload")
    suspend fun uploadMedia(
        @Part file: MultipartBody.Part,
        @Part("kind") kind: RequestBody,
    ): UploadMediaResponse
}
