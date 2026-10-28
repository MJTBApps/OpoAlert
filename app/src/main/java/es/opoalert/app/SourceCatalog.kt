package es.opoalert.app

/** Solo se ofrecen fuentes que ya tienen un lector y feed auditados. */
data class BulletinTerritory(val name: String, val sources: List<Province>)
data class BulletinCommunity(val name: String, val territories: List<BulletinTerritory>) {
    val sourceCount: Int get() = territories.sumOf { it.sources.size }
}

/**
 * La localizacion es un grupo de navegacion, NUNCA una ubicacion del movil.
 * Al integrar una nueva fuente hay que indicar su provincia y comunidad aqui.
 */
object SourceCatalog {
    private data class Territory(val community: String, val province: String)

    private fun territoryOf(source: Province): Territory? = when (source) {
        Province.BOE -> null
        Province.VALENCIA -> Territory("Comunidad Valenciana", "Valencia")
        Province.ALICANTE -> Territory("Comunidad Valenciana", "Alicante")
        Province.CASTELLON -> Territory("Comunidad Valenciana", "Castellón")
        Province.BARCELONA, Province.BARCELONA_BOP -> Territory("Cataluña", "Barcelona")
        Province.GIRONA, Province.GIRONA_BOP -> Territory("Cataluña", "Girona")
        Province.LLEIDA -> Territory("Cataluña", "Lleida")
        Province.HUESCA -> Territory("Aragón", "Huesca")
        Province.TERUEL -> Territory("Aragón", "Teruel")
        Province.ZARAGOZA -> Territory("Aragón", "Zaragoza")
        Province.CADIZ -> Territory("Andalucía", "Cádiz")
        Province.TARRAGONA, Province.TARRAGONA_BOP -> Territory("Cataluña", "Tarragona")
    }

    private val communityOrder = listOf("Comunidad Valenciana", "Cataluña", "Aragón", "Andalucía")

    private val provinceOrder = mapOf(
        "Comunidad Valenciana" to listOf("Valencia", "Alicante", "Castellón"),
        "Cataluña" to listOf("Barcelona", "Girona", "Lleida", "Tarragona"),
        "Aragón" to listOf("Huesca", "Teruel", "Zaragoza"),
        "Andalucía" to listOf("Almería", "Cádiz", "Córdoba", "Granada", "Huelva", "Jaén", "Málaga", "Sevilla"),
    )

    fun groups(sources: List<Province> = Province.entries): List<BulletinCommunity> {
        val placed = sources.filter { it != Province.BOE }.groupBy { territoryOf(it)!!.community }
        return placed.map { (community, values) ->
            val places = values.groupBy { territoryOf(it)!!.province }
            val ranking = provinceOrder[community].orEmpty()
            BulletinCommunity(community,
                places.map { (name, provincialSources) ->
                    BulletinTerritory(name, provincialSources.sortedBy { if (isCido(it)) 1 else 0 })
                }.sortedWith(compareBy<BulletinTerritory> {
                    val index = ranking.indexOf(it.name)
                    if (index < 0) Int.MAX_VALUE else index
                }.thenBy { it.name })
            )
        }.sortedWith(compareBy<BulletinCommunity> {
            val index = communityOrder.indexOf(it.name)
            if (index < 0) Int.MAX_VALUE else index
        }.thenBy { it.name })
    }

    fun isCido(source: Province): Boolean = source in setOf(
        Province.BARCELONA, Province.GIRONA, Province.LLEIDA, Province.TARRAGONA
    )

    fun sourceName(source: Province): String =
        if (source == Province.BOE) "BOE · toda España"
        else if (isCido(source)) "CIDO · procesos selectivos"
        else "BOP · boletín provincial"
}
