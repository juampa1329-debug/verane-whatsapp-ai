package com.verane.mobile.core

import android.content.Context
import com.verane.mobile.core.data.AppPreferences
import com.verane.mobile.core.repository.VeraneRepository

class AppGraph(context: Context) {
    val preferences = AppPreferences(context)
    val repository = VeraneRepository(preferences)
}
