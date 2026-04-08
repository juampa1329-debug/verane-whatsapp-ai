package com.verane.mobile.core.network

import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import com.verane.mobile.BuildConfig
import com.verane.mobile.core.data.AppConfig
import kotlinx.serialization.ExperimentalSerializationApi
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import java.util.concurrent.TimeUnit

@OptIn(ExperimentalSerializationApi::class)
object ApiClient {
    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
        explicitNulls = false
        coerceInputValues = true
    }

    fun service(config: AppConfig): VeraneApiService {
        val client = buildClient(
            token = config.securityToken,
            actorName = config.actorName,
        )
        return Retrofit.Builder()
            .baseUrl(toRetrofitBase(config.apiBase))
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(VeraneApiService::class.java)
    }

    private fun toRetrofitBase(raw: String): String {
        val clean = raw.trim()
            .ifBlank { "https://backend.perfumesverane.com" }
            .removeSuffix("/")
        return "$clean/"
    }

    private fun buildClient(token: String, actorName: String): OkHttpClient {
        val logger = HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) {
                HttpLoggingInterceptor.Level.BODY
            } else {
                HttpLoggingInterceptor.Level.NONE
            }
        }

        return OkHttpClient.Builder()
            .connectTimeout(20, TimeUnit.SECONDS)
            .readTimeout(45, TimeUnit.SECONDS)
            .writeTimeout(45, TimeUnit.SECONDS)
            .addInterceptor { chain ->
                val original = chain.request()
                val builder = original.newBuilder()
                if (token.isNotBlank()) {
                    builder.header("Authorization", "Bearer $token")
                }
                if (actorName.isNotBlank()) {
                    builder.header("X-Actor", actorName)
                    builder.header("X-Admin-User", actorName)
                }
                chain.proceed(builder.build())
            }
            .addInterceptor(logger)
            .build()
    }
}
