package com.verane.mobile.feature.web

import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView

@Composable
fun WebToolsScreen(
    initialUrl: String,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    var targetUrl by remember(initialUrl) { mutableStateOf(initialUrl) }
    var loadedUrl by remember(initialUrl) { mutableStateOf(initialUrl) }

    val webView = remember(context) {
        WebView(context).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.cacheMode = WebSettings.LOAD_DEFAULT
            settings.mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
            webViewClient = WebViewClient()
            webChromeClient = WebChromeClient()
        }
    }

    DisposableEffect(Unit) {
        onDispose {
            webView.stopLoading()
            webView.destroy()
        }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text(
            text = "Modulos avanzados (Dashboard/Marketing/Security) en vista web movil",
            style = MaterialTheme.typography.titleSmall,
        )
        OutlinedTextField(
            value = targetUrl,
            onValueChange = { targetUrl = it },
            label = { Text("URL") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        Button(
            onClick = {
                loadedUrl = targetUrl
                webView.loadUrl(loadedUrl)
            },
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text("Cargar")
        }
        AndroidView(
            factory = {
                webView.apply {
                    loadUrl(loadedUrl)
                }
            },
            update = {
                if (it.url != loadedUrl) {
                    it.loadUrl(loadedUrl)
                }
            },
            modifier = Modifier.fillMaxSize(),
        )
    }
}
