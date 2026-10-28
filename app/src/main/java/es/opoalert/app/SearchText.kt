package es.opoalert.app

import java.text.Normalizer
import java.util.Locale

object SearchText {
    private val combiningMarks = Regex("\\p{M}+")
    private const val ENYE_MARKER = "\uE000"

    fun normalize(text: String): String {
        val lowercase = Normalizer.normalize(text, Normalizer.Form.NFC)
            .lowercase(Locale.ROOT)
            .replace("ñ", ENYE_MARKER)
        val decomposed = Normalizer.normalize(lowercase, Normalizer.Form.NFD)
        return combiningMarks.replace(decomposed, "").replace(ENYE_MARKER, "ñ")
    }

    fun matchesNormalized(normalizedQuery: String, vararg values: String): Boolean =
        normalizedQuery.isEmpty() || values.any { normalize(it).contains(normalizedQuery) }
}
