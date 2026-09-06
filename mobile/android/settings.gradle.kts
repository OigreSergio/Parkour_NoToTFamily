pluginManagement {
    val flutterSdkPath = run {
        val properties = java.util.Properties()
        file("local.properties").inputStream().use { properties.load(it) }
        val flutterSdkPath = properties.getProperty("flutter.sdk")
        require(flutterSdkPath != null) { "flutter.sdk not set in local.properties" }
        flutterSdkPath
    }

    includeBuild("$flutterSdkPath/packages/flutter_tools/gradle")

    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

plugins {
    id("dev.flutter.flutter-plugin-loader") version "1.0.0"
    id("com.android.application") version "8.7.0" apply false
    // Kotlin 2.x is required by the Flutter Gradle plugin: on 1.8.22 the
    // build dies during configuration with
    // "KotlinAndroidProjectExtension.compilerOptions", an API that only exists
    // from Kotlin 2.0 on. Nothing in the app's own Kotlin (a single
    // MainActivity) depends on the version.
    id("org.jetbrains.kotlin.android") version "2.1.0" apply false
}

include(":app")
