# Project-specific ProGuard rules.

# Keep Kotlin serialization metadata used by Retrofit converter.
-keep class kotlinx.serialization.** { *; }
-keep class **$$serializer { *; }
-keepclassmembers class * {
    @kotlinx.serialization.SerialName <fields>;
}

# Keep Firebase messaging service and crashlytics classes.
-keep class com.verane.mobile.push.VeraneFirebaseMessagingService { *; }
-keep class com.google.firebase.** { *; }
