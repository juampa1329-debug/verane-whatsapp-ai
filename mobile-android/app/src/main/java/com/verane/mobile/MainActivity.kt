package com.verane.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.verane.mobile.ui.VeraneMobileRoot
import com.verane.mobile.ui.theme.VeraneTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val app = application as VeraneApp
        setContent {
            VeraneTheme {
                VeraneMobileRoot(graph = app.appGraph)
            }
        }
    }
}
