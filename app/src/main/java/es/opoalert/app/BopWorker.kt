package es.opoalert.app

import android.content.Context
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkerParameters
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

class BopWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {
    override suspend fun doWork(): Result = try {
        val result = Repository.sync(applicationContext)
        Notifications.show(applicationContext, result.alertMatches)
        Result.success()
    } catch (_: Exception) {
        Result.retry()
    }

    companion object {
        fun schedule(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()
            // Cada hora: los feeds se publican cuatro veces al día y así las
            // novedades llegan al móvil poco después. UPDATE aplica el intervalo
            // también a las instalaciones que tenían el antiguo de 6 horas.
            val request = PeriodicWorkRequestBuilder<BopWorker>(1, TimeUnit.HOURS)
                .setConstraints(constraints)
                .build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                "opoalert_bop_scan", ExistingPeriodicWorkPolicy.UPDATE, request
            )
        }
    }
}
