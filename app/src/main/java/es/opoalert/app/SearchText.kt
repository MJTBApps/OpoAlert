package es.opoalert.app

import java.text.Normalizer
import java.util.Locale

/**
 * Search-only normalization. Text from official announcements remains unchanged.
 *
 * Accent marks (á, é, í, ó, ú, ü) are ignored, as is casing. The Spanish
 * letter ñ remains distinct from n, because it is a separate letter.
 */
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

    /**
     * Accepts a normalized query; normalizes each candidate just for matching.
     * Treats empty queries as "show all" and preserves existing substring search.
     */
    fun matchesNormalized(normalizedQuery: String, vararg values: String): Boolean {
        return normalizedQuery.isEmpty() || values.any { normalize(it).contains(normalizedQuery) }
    }
}
