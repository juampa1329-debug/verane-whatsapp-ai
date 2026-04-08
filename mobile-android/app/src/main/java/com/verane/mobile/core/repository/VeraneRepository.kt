package com.verane.mobile.core.repository

import com.verane.mobile.core.data.AppConfig
import com.verane.mobile.core.data.AppPreferences
import com.verane.mobile.core.network.*
import kotlinx.coroutines.flow.first
import kotlinx.serialization.json.JsonObject
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.HttpException

class VeraneRepository(
    private val preferences: AppPreferences,
) {
    val configFlow = preferences.configFlow

    suspend fun currentConfig(): AppConfig = preferences.configFlow.first()

    suspend fun saveConfig(
        apiBase: String,
        securityToken: String,
        webAppBase: String,
        backgroundSyncEnabled: Boolean,
        securityRole: String,
        actorName: String,
    ) {
        preferences.saveConfig(
            apiBase = apiBase,
            securityToken = securityToken,
            webAppBase = webAppBase,
            backgroundSyncEnabled = backgroundSyncEnabled,
            securityRole = securityRole,
            actorName = actorName,
        )
    }

    suspend fun saveFirebaseToken(token: String) {
        preferences.saveFirebaseToken(token)
    }

    suspend fun dashboardOverview(range: String = "7d"): DashboardOverviewResponse = withApi {
        it.getDashboardOverview(range = range)
    }

    suspend fun dashboardFunnel(): DashboardFunnelResponse = withApi {
        it.getDashboardFunnel()
    }

    suspend fun dashboardCampaigns(range: String = "30d"): DashboardCampaignsResponse = withApi {
        it.getDashboardCampaigns(range = range)
    }

    suspend fun dashboardRemarketing(): DashboardRemarketingResponse = withApi {
        it.getDashboardRemarketing()
    }

    suspend fun campaignEngineStatus(): CampaignEngineStatusResponse = withApi {
        it.getCampaignEngineStatus()
    }

    suspend fun campaignEngineTick(batchSize: Int = 20, sendDelayMs: Int = 0): JsonObject = withApi {
        it.tickCampaignEngine(batchSize = batchSize, sendDelayMs = sendDelayMs)
    }

    suspend fun remarketingEngineStatus(): RemarketingEngineStatusResponse = withApi {
        it.getRemarketingEngineStatus()
    }

    suspend fun remarketingEngineTick(
        limit: Int = 300,
        flowId: Int = 0,
        channel: String = "all",
    ): JsonObject = withApi {
        it.tickRemarketingEngine(limit = limit, flowId = flowId, channel = channel)
    }

    suspend fun listConversations(
        search: String,
        channel: String = "all",
        takeover: String = "all",
        unread: String = "all",
        tags: String = "",
    ): List<ConversationDto> = withApi {
        it.getConversations(
            search = search,
            channel = channel,
            takeover = takeover,
            unread = unread,
            tags = tags,
        ).conversations
    }

    suspend fun listMessages(phone: String, channel: String = "all"): List<MessageDto> = withApi {
        it.getMessages(phone = phone, channel = channel).messages
    }

    suspend fun markConversationRead(phone: String) {
        withApi { it.markConversationRead(phone = phone) }
    }

    suspend fun setTakeover(phone: String, enabled: Boolean) {
        withApi {
            it.setTakeover(
                request = TakeoverRequest(
                    phone = phone,
                    takeover = enabled,
                )
            )
        }
    }

    suspend fun sendTextMessage(
        phone: String,
        channel: String,
        text: String,
    ) {
        withApi {
            it.ingestMessage(
                request = IngestRequest(
                    phone = phone,
                    channel = normalizeChannel(channel),
                    direction = "out",
                    msgType = "text",
                    text = text,
                )
            )
        }
    }

    suspend fun sendMediaMessage(
        phone: String,
        channel: String,
        bytes: ByteArray,
        fileName: String,
        mimeType: String,
        kind: String,
        caption: String,
        durationSec: Int? = null,
    ) {
        withApi { api ->
            val reqBody = bytes.toRequestBody(mimeType.toMediaTypeOrNull())
            val filePart = MultipartBody.Part.createFormData("file", fileName, reqBody)
            val kindPart = kind.toRequestBody("text/plain".toMediaTypeOrNull())
            val uploaded = api.uploadMedia(file = filePart, kind = kindPart)
            api.ingestMessage(
                request = IngestRequest(
                    phone = phone,
                    channel = normalizeChannel(channel),
                    direction = "out",
                    msgType = normalizeMessageType(kind),
                    text = "",
                    mediaId = uploaded.mediaId,
                    mediaCaption = caption,
                    mimeType = uploaded.mimeType.ifBlank { mimeType },
                    fileName = uploaded.filename.ifBlank { fileName },
                    fileSize = bytes.size.toLong(),
                    durationSec = durationSec,
                )
            )
        }
    }

    suspend fun listWcProducts(
        q: String = "",
        page: Int = 1,
        perPage: Int = 12,
    ): List<WcProductDto> = withApi {
        it.getWcProducts(q = q, page = page, perPage = perPage).products
    }

    suspend fun sendWcProduct(
        phone: String,
        productId: Long,
        caption: String = "",
    ): WcSendProductResponse = withApi {
        it.sendWcProduct(
            request = WcSendProductRequest(
                phone = phone,
                productId = productId,
                caption = caption,
            ),
        )
    }

    suspend fun listCustomers(search: String, pageSize: Int = 50): List<CustomerDto> = withApi {
        it.getCustomers(search = search, page = 1, pageSize = pageSize).customers
    }

    suspend fun getCustomer(phone: String): CustomerDto? = withApi {
        it.getCustomer(phone = phone).customer
    }

    suspend fun updateCustomer(phone: String, patch: CustomerPatchRequest): CustomerDto? = withApi {
        it.patchCustomer(phone = phone, body = patch).customer
    }

    suspend fun listSegments(active: String = "all"): List<SegmentDto> = withApi {
        it.getSegments(active = active).segments
    }

    suspend fun listTemplates(
        channel: String = "all",
        status: String = "all",
        search: String = "",
    ): List<TemplateDto> = withApi {
        it.getTemplates(
            status = status,
            channel = channel,
            category = "",
            search = search,
        ).templates
    }

    suspend fun createTemplate(
        name: String,
        category: String,
        channel: String,
        body: String,
        renderMode: String = "chat",
        status: String = "draft",
    ): TemplateDto? = withApi {
        it.createTemplate(
            request = TemplateCreateRequest(
                name = name,
                category = category,
                channel = normalizeChannel(channel),
                body = body,
                renderMode = renderMode,
                status = status,
            )
        ).template
    }

    suspend fun updateTemplate(
        templateId: Int,
        name: String? = null,
        category: String? = null,
        channel: String? = null,
        body: String? = null,
        renderMode: String? = null,
        status: String? = null,
    ): TemplateDto? = withApi {
        it.patchTemplate(
            templateId = templateId,
            request = TemplatePatchRequest(
                name = name,
                category = category,
                channel = channel?.let { normalizeChannel(it) },
                body = body,
                renderMode = renderMode,
                status = status,
            )
        ).template
    }

    suspend fun deleteTemplate(templateId: Int): JsonObject = withApi {
        it.deleteTemplate(templateId = templateId)
    }

    suspend fun listCampaigns(
        status: String = "all",
        channel: String = "all",
    ): List<CampaignDto> = withApi {
        it.getCampaigns(status = status, channel = channel).campaigns
    }

    suspend fun createCampaign(
        name: String,
        objective: String,
        segmentId: Int?,
        templateId: Int?,
        channel: String,
        status: String = "draft",
    ): CampaignDto? = withApi {
        it.createCampaign(
            request = CampaignCreateRequest(
                name = name,
                objective = objective,
                segmentId = segmentId,
                templateId = templateId,
                status = status,
                scheduledAt = null,
                channel = normalizeChannel(channel),
            )
        ).campaign
    }

    suspend fun launchCampaign(campaignId: Int, maxRecipients: Int = 300): JsonObject = withApi {
        it.launchCampaign(campaignId = campaignId, maxRecipients = maxRecipients)
    }

    suspend fun deleteCampaign(campaignId: Int): JsonObject = withApi {
        it.deleteCampaign(campaignId = campaignId)
    }

    suspend fun listTriggers(
        active: String = "all",
        channel: String = "all",
    ): List<TriggerDto> = withApi {
        it.getTriggers(active = active, channel = channel).triggers
    }

    suspend fun createTrigger(
        name: String,
        channel: String,
        eventType: String = "message_in",
        triggerType: String = "message_flow",
        flowEvent: String = "received",
        cooldownMinutes: Int = 60,
        priority: Int = 100,
        isActive: Boolean = true,
    ): TriggerDto? = withApi {
        it.createTrigger(
            request = TriggerCreateRequest(
                name = name,
                channel = normalizeChannel(channel),
                eventType = eventType,
                triggerType = triggerType,
                flowEvent = flowEvent,
                cooldownMinutes = cooldownMinutes,
                isActive = isActive,
                priority = priority,
            )
        ).trigger
    }

    suspend fun updateTrigger(
        triggerId: Int,
        name: String? = null,
        channel: String? = null,
        eventType: String? = null,
        triggerType: String? = null,
        flowEvent: String? = null,
        cooldownMinutes: Int? = null,
        isActive: Boolean? = null,
        assistantEnabled: Boolean? = null,
        assistantMessageType: String? = null,
        priority: Int? = null,
        blockAi: Boolean? = null,
        stopOnMatch: Boolean? = null,
        onlyWhenNoTakeover: Boolean? = null,
    ): TriggerDto? = withApi {
        it.patchTrigger(
            triggerId = triggerId,
            request = TriggerPatchRequest(
                name = name,
                channel = channel?.let { normalizeChannel(it) },
                eventType = eventType,
                triggerType = triggerType,
                flowEvent = flowEvent,
                cooldownMinutes = cooldownMinutes,
                isActive = isActive,
                assistantEnabled = assistantEnabled,
                assistantMessageType = assistantMessageType,
                priority = priority,
                blockAi = blockAi,
                stopOnMatch = stopOnMatch,
                onlyWhenNoTakeover = onlyWhenNoTakeover,
            )
        ).trigger
    }

    suspend fun toggleTrigger(triggerId: Int, active: Boolean): TriggerDto? = withApi {
        it.patchTrigger(
            triggerId = triggerId,
            request = TriggerPatchRequest(isActive = active),
        ).trigger
    }

    suspend fun deleteTrigger(triggerId: Int): JsonObject = withApi {
        it.deleteTrigger(triggerId = triggerId)
    }

    suspend fun listRemarketingFlows(channel: String = "all"): List<RemarketingFlowDto> = withApi {
        it.getRemarketingFlows(channel = channel).flows
    }

    suspend fun createRemarketingFlow(
        name: String,
        channel: String,
        isActive: Boolean = false,
    ): RemarketingFlowDto? = withApi {
        it.createRemarketingFlow(
            request = RemarketingFlowCreateRequest(
                name = name,
                channel = normalizeChannel(channel),
                isActive = isActive,
            )
        ).flow
    }

    suspend fun updateRemarketingFlow(
        flowId: Int,
        name: String? = null,
        channel: String? = null,
        isActive: Boolean? = null,
    ): RemarketingFlowDto? = withApi {
        it.patchRemarketingFlow(
            flowId = flowId,
            request = RemarketingFlowPatchRequest(
                name = name,
                channel = channel?.let { normalizeChannel(it) },
                isActive = isActive,
            )
        ).flow
    }

    suspend fun deleteRemarketingFlow(flowId: Int): JsonObject = withApi {
        it.deleteRemarketingFlow(flowId = flowId)
    }

    suspend fun listRemarketingFlowSteps(flowId: Int): List<RemarketingStepDto> = withApi {
        it.getRemarketingFlowSteps(flowId = flowId).steps
    }

    suspend fun createRemarketingStep(
        flowId: Int,
        stepOrder: Int,
        stageName: String,
        waitMinutes: Int,
        templateId: Int?,
    ): RemarketingStepDto? = withApi {
        it.createRemarketingStep(
            flowId = flowId,
            request = RemarketingStepCreateRequest(
                stepOrder = stepOrder,
                stageName = stageName,
                waitMinutes = waitMinutes,
                templateId = templateId,
            )
        ).step
    }

    suspend fun updateRemarketingStep(
        stepId: Int,
        stepOrder: Int? = null,
        stageName: String? = null,
        waitMinutes: Int? = null,
        templateId: Int? = null,
    ): RemarketingStepDto? = withApi {
        it.patchRemarketingStep(
            stepId = stepId,
            request = RemarketingStepPatchRequest(
                stepOrder = stepOrder,
                stageName = stageName,
                waitMinutes = waitMinutes,
                templateId = templateId,
            )
        ).step
    }

    suspend fun deleteRemarketingStep(stepId: Int): JsonObject = withApi {
        it.deleteRemarketingStep(stepId = stepId)
    }

    suspend fun listRemarketingEnrollments(
        flowId: Int,
        state: String = "all",
        limit: Int = 120,
    ): List<RemarketingEnrollmentDto> = withApi {
        it.getRemarketingEnrollments(flowId = flowId, state = state, limit = limit).enrollments
    }

    suspend fun dispatchRemarketingFlow(
        flowId: Int,
        limit: Int = 600,
        includeHold: Boolean = false,
    ): JsonObject = withApi {
        it.dispatchRemarketingFlow(
            flowId = flowId,
            request = RemarketingDispatchRequest(limit = limit, includeHold = includeHold),
        )
    }

    suspend fun dispatchRemarketingStep(
        stepId: Int,
        limit: Int = 600,
        includeHold: Boolean = false,
    ): JsonObject = withApi {
        it.dispatchRemarketingStep(
            stepId = stepId,
            request = RemarketingDispatchRequest(limit = limit, includeHold = includeHold),
        )
    }

    suspend fun securityAuthMode(): SecurityAuthModeResponse = withApi {
        it.getSecurityAuthMode()
    }

    suspend fun securityState(
        auditLevel: String = "all",
        auditLimit: Int = 50,
    ): SecurityStateResponse = withApi {
        it.getSecurityState(auditLevel = auditLevel, auditLimit = auditLimit)
    }

    suspend fun securityRotationStatus(): SecurityRotationStatusResponse = withApi {
        it.getSecurityRotationStatus()
    }

    suspend fun securityRotationTick(limit: Int = 60): SecurityRotationTickResponse = withApi {
        it.tickSecurityRotation(limit = limit)
    }

    suspend fun updateSecurityPolicy(
        passwordMinLength: Int? = null,
        requireSpecialChars: Boolean? = null,
        accessTokenMinutes: Int? = null,
        refreshTokenDays: Int? = null,
        sessionIdleMinutes: Int? = null,
        sessionAbsoluteHours: Int? = null,
        maxFailedAttempts: Int? = null,
        lockMinutes: Int? = null,
        forcePasswordRotationDays: Int? = null,
    ): SecurityPatchResultResponse = withApi {
        it.updateSecurityPolicy(
            request = SecurityPolicyPatchRequest(
                passwordMinLength = passwordMinLength,
                requireSpecialChars = requireSpecialChars,
                accessTokenMinutes = accessTokenMinutes,
                refreshTokenDays = refreshTokenDays,
                sessionIdleMinutes = sessionIdleMinutes,
                sessionAbsoluteHours = sessionAbsoluteHours,
                maxFailedAttempts = maxFailedAttempts,
                lockMinutes = lockMinutes,
                forcePasswordRotationDays = forcePasswordRotationDays,
            )
        )
    }

    suspend fun updateSecurityMfa(
        enforceForAdmins: Boolean? = null,
        enforceForSupervisors: Boolean? = null,
        allowForAgents: Boolean? = null,
        backupCodesEnabled: Boolean? = null,
    ): SecurityPatchResultResponse = withApi {
        it.updateSecurityMfa(
            request = SecurityMfaPatchRequest(
                enforceForAdmins = enforceForAdmins,
                enforceForSupervisors = enforceForSupervisors,
                allowForAgents = allowForAgents,
                backupCodesEnabled = backupCodesEnabled,
            )
        )
    }

    suspend fun updateSecurityAlerts(
        failedLoginAlert: Boolean? = null,
        suspiciousIpAlert: Boolean? = null,
        securityChangeAlert: Boolean? = null,
        webhookFailureAlert: Boolean? = null,
        channelEmail: Boolean? = null,
        channelWhatsapp: Boolean? = null,
    ): SecurityPatchResultResponse = withApi {
        it.updateSecurityAlerts(
            request = SecurityAlertsPatchRequest(
                failedLoginAlert = failedLoginAlert,
                suspiciousIpAlert = suspiciousIpAlert,
                securityChangeAlert = securityChangeAlert,
                webhookFailureAlert = webhookFailureAlert,
                channelEmail = channelEmail,
                channelWhatsapp = channelWhatsapp,
            )
        )
    }

    suspend fun createSecurityUser(
        name: String,
        email: String,
        role: String = "agente",
        twofa: Boolean = false,
        active: Boolean = true,
        password: String? = null,
    ): SecurityUserEnvelopeResponse = withApi {
        it.createSecurityUser(
            request = SecurityUserCreateRequest(
                name = name,
                email = email,
                role = role,
                twofa = twofa,
                active = active,
                password = password,
            )
        )
    }

    suspend fun patchSecurityUser(
        userId: Int,
        name: String? = null,
        email: String? = null,
        role: String? = null,
        twofa: Boolean? = null,
        active: Boolean? = null,
    ): SecurityUserEnvelopeResponse = withApi {
        it.patchSecurityUser(
            userId = userId,
            request = SecurityUserPatchRequest(
                name = name,
                email = email,
                role = role,
                twofa = twofa,
                active = active,
            )
        )
    }

    suspend fun resetSecurityUserPassword(
        userId: Int,
        password: String? = null,
    ): SecurityPasswordResetResponse = withApi {
        it.resetSecurityUserPassword(
            userId = userId,
            request = SecurityPasswordResetRequest(password = password),
        )
    }

    suspend fun setupSecurityUser2fa(userId: Int): SecurityTwofaSetupResponse = withApi {
        it.setupSecurityUser2fa(userId = userId)
    }

    suspend fun verifySecurityUser2fa(
        userId: Int,
        code: String,
    ): SecurityTwofaVerifyResponse = withApi {
        it.verifySecurityUser2fa(
            userId = userId,
            request = SecurityTwofaVerifyRequest(code = code),
        )
    }

    suspend fun disableSecurityUser2fa(userId: Int): SecurityTwofaVerifyResponse = withApi {
        it.disableSecurityUser2fa(userId = userId)
    }

    suspend fun revokeSecuritySession(sessionId: String): SecuritySessionRevokeResponse = withApi {
        it.revokeSecuritySession(sessionId = sessionId)
    }

    suspend fun revokeAllSecuritySessions(): SecurityRevokeAllResponse = withApi {
        it.revokeAllSecuritySessions()
    }

    suspend fun createSecurityKey(
        name: String,
        scope: String = "general",
        rotationDays: Int = 90,
    ): SecurityKeyEnvelopeResponse = withApi {
        it.createSecurityKey(
            request = SecurityKeyCreateRequest(
                name = name,
                scope = scope.trim().ifBlank { "general" },
                rotationDays = rotationDays,
            )
        )
    }

    suspend fun rotateSecurityKey(keyId: Int): SecurityKeyEnvelopeResponse = withApi {
        it.rotateSecurityKey(keyId = keyId)
    }

    suspend fun patchSecurityKey(
        keyId: Int,
        name: String? = null,
        scope: String? = null,
        isActive: Boolean? = null,
        rotationDays: Int? = null,
    ): SecurityKeyEnvelopeResponse = withApi {
        it.patchSecurityKey(
            keyId = keyId,
            request = SecurityKeyPatchRequest(
                name = name,
                scope = scope,
                isActive = isActive,
                rotationDays = rotationDays,
            )
        )
    }

    suspend fun revealSecurityKey(keyId: Int): SecurityRevealKeyResponse = withApi {
        it.revealSecurityKey(keyId = keyId)
    }

    suspend fun listSecurityAudit(
        level: String = "all",
        limit: Int = 120,
    ): List<SecurityAuditEventDto> = withApi {
        it.getSecurityAudit(level = level, limit = limit).events
    }

    suspend fun registerMobilePushToken(
        token: String,
        platform: String = "android",
        appVersion: String = "",
        deviceId: String = "",
        role: String = "agente",
        actor: String = "",
        notificationsEnabled: Boolean = true,
    ): MobilePushRegisterResponse = withApi {
        val request = MobilePushRegisterRequest(
            token = token,
            platform = platform,
            appVersion = appVersion,
            deviceId = deviceId,
            role = role,
            actor = actor,
            notificationsEnabled = notificationsEnabled,
        )
        try {
            it.registerMobilePushToken(request = request)
        } catch (e: HttpException) {
            if (e.code() != 404) throw e
            it.registerMobilePushTokenCompat(request = request)
        }
    }

    suspend fun unregisterMobilePushToken(token: String): MobilePushUnregisterResponse = withApi {
        val request = MobilePushUnregisterRequest(token = token)
        try {
            it.unregisterMobilePushToken(request = request)
        } catch (e: HttpException) {
            if (e.code() != 404) throw e
            it.unregisterMobilePushTokenCompat(request = request)
        }
    }

    suspend fun mobilePushState(): MobilePushStateResponse = withApi {
        try {
            it.getMobilePushState()
        } catch (e: HttpException) {
            if (e.code() != 404) throw e
            it.getMobilePushStateCompat()
        }
    }

    suspend fun testMobilePush(
        title: String,
        body: String,
        eventType: String = "manual_test",
        roleScope: String = "all",
    ): MobilePushTestResponse = withApi {
        val request = MobilePushTestRequest(
            title = title,
            body = body,
            eventType = eventType,
            roleScope = roleScope,
        )
        try {
            it.testMobilePush(request = request)
        } catch (e: HttpException) {
            if (e.code() != 404) throw e
            it.testMobilePushCompat(request = request)
        }
    }

    suspend fun getAiSettings(): AiSettingsDto = withApi {
        it.getAiSettings()
    }

    suspend fun updateAiSettings(payload: AiSettingsUpdateRequest): AiSettingsDto = withApi {
        it.updateAiSettings(request = payload)
    }

    suspend fun getAiModelsCatalog(): AiModelsCatalogResponse = withApi {
        it.getAiModelsCatalog()
    }

    suspend fun processAiMessage(phone: String, text: String): AiProcessResponse = withApi {
        it.processAiMessage(request = AiProcessRequest(phone = phone, text = text))
    }

    suspend fun listKnowledgeFiles(
        active: String = "all",
        limit: Int = 200,
    ): List<KnowledgeFileDto> = withApi {
        it.getKnowledgeFiles(active = active, limit = limit)
    }

    suspend fun uploadKnowledgeFile(
        bytes: ByteArray,
        fileName: String,
        mimeType: String,
        notes: String = "",
    ): KnowledgeUploadResponse = withApi { api ->
        val reqBody = bytes.toRequestBody(mimeType.toMediaTypeOrNull())
        val filePart = MultipartBody.Part.createFormData("file", fileName, reqBody)
        val notesPart = notes.toRequestBody("text/plain".toMediaTypeOrNull())
        api.uploadKnowledgeFile(file = filePart, notes = notesPart)
    }

    suspend fun deleteKnowledgeFile(fileId: String): ApiOkResponse = withApi {
        it.deleteKnowledgeFile(fileId = fileId)
    }

    suspend fun reindexKnowledgeFile(fileId: String): JsonObject = withApi {
        it.reindexKnowledgeFile(fileId = fileId)
    }

    suspend fun listKnowledgeWebSources(
        active: String = "all",
        limit: Int = 200,
    ): List<KnowledgeWebSourceDto> = withApi {
        it.getKnowledgeWebSources(active = active, limit = limit)
    }

    suspend fun createKnowledgeWebSource(
        url: String,
        sourceName: String = "",
        notes: String = "",
        isActive: Boolean = true,
        autoSync: Boolean = true,
        syncIntervalMin: Int = 360,
        timeoutSec: Int = 20,
    ): KnowledgeWebSourceDto = withApi {
        it.createKnowledgeWebSource(
            request = KnowledgeWebSourceCreateRequest(
                url = url,
                sourceName = sourceName,
                notes = notes,
                isActive = isActive,
                autoSync = autoSync,
                syncIntervalMin = syncIntervalMin,
                timeoutSec = timeoutSec,
            )
        )
    }

    suspend fun updateKnowledgeWebSource(
        sourceId: String,
        url: String? = null,
        sourceName: String? = null,
        notes: String? = null,
        isActive: Boolean? = null,
        autoSync: Boolean? = null,
        syncIntervalMin: Int? = null,
        timeoutSec: Int? = null,
    ): KnowledgeWebSourceDto = withApi {
        it.updateKnowledgeWebSource(
            sourceId = sourceId,
            request = KnowledgeWebSourcePatchRequest(
                url = url,
                sourceName = sourceName,
                notes = notes,
                isActive = isActive,
                autoSync = autoSync,
                syncIntervalMin = syncIntervalMin,
                timeoutSec = timeoutSec,
            )
        )
    }

    suspend fun deleteKnowledgeWebSource(sourceId: String): ApiOkResponse = withApi {
        it.deleteKnowledgeWebSource(sourceId = sourceId)
    }

    suspend fun syncKnowledgeWebSource(sourceId: String): KnowledgeSyncResultResponse = withApi {
        it.syncKnowledgeWebSource(sourceId = sourceId)
    }

    suspend fun syncDueKnowledgeWebSources(limit: Int = 10): KnowledgeSyncDueResponse = withApi {
        it.syncDueKnowledgeWebSources(limit = limit)
    }

    suspend fun testAiTts(
        text: String,
        provider: String? = null,
        voiceId: String? = null,
        modelId: String? = null,
    ): Pair<String, ByteArray> = withApi { api ->
        val body = api.testAiTts(
            request = AiTtsRequest(
                text = text,
                provider = provider,
                voiceId = voiceId,
                modelId = modelId,
            )
        )
        val bytes = body.bytes()
        val mime = body.contentType()?.toString().orEmpty()
        Pair(mime, bytes)
    }

    suspend fun loadSyncState(): Pair<Int, String> = preferences.syncStateFlow.first()

    suspend fun saveSyncState(unreadTotal: Int, topConversationTs: String) {
        preferences.saveSyncState(unreadTotal, topConversationTs)
    }

    suspend fun mediaProxyUrl(mediaId: String): String {
        val cfg = currentConfig()
        return "${cfg.apiBase.removeSuffix("/")}/api/media/proxy/$mediaId"
    }

    private suspend fun <T> withApi(block: suspend (VeraneApiService) -> T): T {
        val config = currentConfig()
        val api = ApiClient.service(config)
        return block(api)
    }

    private fun normalizeChannel(raw: String): String {
        return when (raw.trim().lowercase()) {
            "whatsapp", "facebook", "instagram", "tiktok" -> raw.trim().lowercase()
            else -> "whatsapp"
        }
    }

    private fun normalizeMessageType(kind: String): String {
        return when (kind.trim().lowercase()) {
            "image", "video", "audio", "document" -> kind.trim().lowercase()
            else -> "document"
        }
    }
}
