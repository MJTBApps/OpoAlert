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
        Province.MURCIA_BORM -> Territory("Región de Murcia", "Murcia")
        Province.ALAVA_BOTHA -> Territory("País Vasco", "Álava")
        Province.BIZKAIA_BOB -> Territory("País Vasco", "Bizkaia")
        Province.GIPUZKOA_BOG -> Territory("País Vasco", "Gipuzkoa")
        Province.PAIS_VASCO_BOPV -> Territory("País Vasco", "Diario autonómico")
        Province.GALICIA_CORUNA -> Territory("Galicia", "A Coruña")
        Province.GALICIA_LUGO -> Territory("Galicia", "Lugo")
        Province.GALICIA_OURENSE -> Territory("Galicia", "Ourense")
        Province.GALICIA_PONTEVEDRA -> Territory("Galicia", "Pontevedra")
        Province.GALICIA_DOG -> Territory("Galicia", "Diario autonómico")
        Province.CATALUNA_DOGC -> Territory("Cataluña", "Diario autonómico")
        Province.ARAGON_BOA -> Territory("Aragón", "Diario autonómico")
        Province.ANDALUCIA_BOJA -> Territory("Andalucía", "Diario autonómico")
        Province.VALENCIA_DOGV -> Territory("Comunidad Valenciana", "Diario autonómico")
        Province.BALEARES_BOIB -> Territory("Illes Balears", "Todas las islas")
        Province.CANARIAS_BOC -> Territory("Canarias", "Diario autonómico")
        Province.LAS_PALMAS_BOP -> Territory("Canarias", "Las Palmas")
        Province.SANTA_CRUZ_BOP -> Territory("Canarias", "Santa Cruz de Tenerife")
        Province.MELILLA_BOME -> Territory("Ciudad Autónoma de Melilla", "Melilla")
        Province.RIOJA_BOR -> Territory("La Rioja", "Diario autonómico")
        Province.BADAJOZ_BOP -> Territory("Extremadura", "Badajoz")
        Province.CACERES_BOP -> Territory("Extremadura", "Cáceres")
        Province.EXTREMADURA_DOE -> Territory("Extremadura", "Diario autonómico")
        Province.MADRID -> Territory("Comunidad de Madrid", "Madrid")
        Province.AVILA -> Territory("Castilla y León", "Ávila")
        Province.LEON_BOP -> Territory("Castilla y León", "León")
        Province.PALENCIA_BOP -> Territory("Castilla y León", "Palencia")
        Province.ZAMORA_BOP -> Territory("Castilla y León", "Zamora")
        Province.SALAMANCA_BOP -> Territory("Castilla y León", "Salamanca")
        Province.SEGOVIA_BOP -> Territory("Castilla y León", "Segovia")
        Province.SORIA_BOP -> Territory("Castilla y León", "Soria")
        Province.CYL_BOCYL -> Territory("Castilla y León", "Diario autonómico")
        Province.HUELVA_BOP -> Territory("Andalucía", "Huelva")
        Province.ALBACETE -> Territory("Castilla-La Mancha", "Albacete")
        Province.CIUDAD_REAL -> Territory("Castilla-La Mancha", "Ciudad Real")
        Province.CUENCA -> Territory("Castilla-La Mancha", "Cuenca")
        Province.GUADALAJARA -> Territory("Castilla-La Mancha", "Guadalajara")
        Province.TOLEDO -> Territory("Castilla-La Mancha", "Toledo")
        Province.CLM_DOCM -> Territory("Castilla-La Mancha", "Diario autonómico")
        Province.VALENCIA -> Territory("Comunidad Valenciana", "Valencia")
        Province.ALICANTE -> Territory("Comunidad Valenciana", "Alicante")
        Province.CASTELLON -> Territory("Comunidad Valenciana", "Castellón")
        Province.BARCELONA, Province.BARCELONA_BOP -> Territory("Cataluña", "Barcelona")
        Province.GIRONA, Province.GIRONA_BOP -> Territory("Cataluña", "Girona")
        Province.LLEIDA -> Territory("Cataluña", "Lleida")
        Province.HUESCA -> Territory("Aragón", "Huesca")
        Province.TERUEL -> Territory("Aragón", "Teruel")
        Province.ZARAGOZA -> Territory("Aragón", "Zaragoza")
        Province.ALMERIA -> Territory("Andalucía", "Almería")
        Province.CADIZ -> Territory("Andalucía", "Cádiz")
        Province.CORDOBA -> Territory("Andalucía", "Córdoba")
        Province.GRANADA -> Territory("Andalucía", "Granada")
        Province.SEVILLA -> Territory("Andalucía", "Sevilla")
        Province.TARRAGONA, Province.TARRAGONA_BOP -> Territory("Cataluña", "Tarragona")
    }

    private val communityOrder = listOf("Comunidad Valenciana", "Cataluña", "Aragón", "Andalucía", "Comunidad de Madrid", "Castilla-La Mancha", "Castilla y León", "Extremadura", "Región de Murcia", "País Vasco", "Galicia", "Illes Balears", "Canarias", "Ciudad Autónoma de Melilla", "La Rioja")

    private val provinceOrder = mapOf(
        "Comunidad Valenciana" to listOf("Valencia", "Alicante", "Castellón", "Diario autonómico"),
        "Cataluña" to listOf("Barcelona", "Girona", "Lleida", "Tarragona", "Diario autonómico"),
        "Aragón" to listOf("Huesca", "Teruel", "Zaragoza"),
        "Andalucía" to listOf("Almería", "Cádiz", "Córdoba", "Granada", "Huelva", "Jaén", "Málaga", "Sevilla"),
        "Comunidad de Madrid" to listOf("Madrid"),
        "Castilla-La Mancha" to listOf("Albacete", "Ciudad Real", "Cuenca", "Guadalajara", "Toledo", "Diario autonómico"),
        "Castilla y León" to listOf("Ávila", "Burgos", "León", "Palencia", "Salamanca", "Segovia", "Soria", "Valladolid", "Zamora", "Diario autonómico"),
        "Extremadura" to listOf("Badajoz", "Cáceres", "Diario autonómico"),
        "Región de Murcia" to listOf("Murcia"),
        "País Vasco" to listOf("Álava", "Bizkaia", "Gipuzkoa", "Diario autonómico"),
        "Galicia" to listOf("A Coruña", "Lugo", "Ourense", "Pontevedra", "Diario autonómico"),
        "Illes Balears" to listOf("Todas las islas"),
        "Canarias" to listOf("Las Palmas", "Santa Cruz de Tenerife", "Diario autonómico"),
        "Ciudad Autónoma de Melilla" to listOf("Melilla"),
        "La Rioja" to listOf("Diario autonómico"),
        "Aragón" to listOf("Huesca", "Teruel", "Zaragoza", "Diario autonómico"),
        "Andalucía" to listOf("Almería", "Cádiz", "Córdoba", "Granada", "Huelva", "Jaén", "Málaga", "Sevilla", "Diario autonómico"),
    )

    val availableSources: List<Province> = Province.entries.filterNot {
        it == Province.ALBACETE || it == Province.CUENCA
    }

    fun groups(sources: List<Province> = availableSources): List<BulletinCommunity> {
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
        else if (source == Province.MADRID) "BOCM · diario autonómico"
        else if (source == Province.CLM_DOCM) "DOCM · diario autonómico"
        else if (source == Province.CYL_BOCYL) "BOCYL · diario autonómico"
        else if (source == Province.EXTREMADURA_DOE) "DOE · diario autonómico"
        else if (source == Province.MURCIA_BORM) "BORM · boletín autonómico y provincial"
        else if (source == Province.PAIS_VASCO_BOPV) "BOPV · diario autonómico"
        else if (source == Province.ALAVA_BOTHA) "BOTHA · boletín territorial de Álava"
        else if (source == Province.BIZKAIA_BOB) "BOB · boletín territorial de Bizkaia"
        else if (source == Province.GIPUZKOA_BOG) "BOG · boletín territorial de Gipuzkoa"
        else if (source == Province.GALICIA_DOG) "DOG · diario autonómico"
        else if (source == Province.CATALUNA_DOGC) "DOGC · diario autonómico"
        else if (source == Province.ARAGON_BOA) "BOA · diario autonómico"
        else if (source == Province.ANDALUCIA_BOJA) "BOJA · diario autonómico"
        else if (source == Province.VALENCIA_DOGV) "DOGV · diario autonómico"
        else if (source == Province.BALEARES_BOIB) "BOIB · boletín autonómico e insular"
        else if (source == Province.CANARIAS_BOC) "BOC · diario autonómico"
        else if (source == Province.MELILLA_BOME) "BOME · boletín de la ciudad autónoma"
        else if (source == Province.RIOJA_BOR) "BOR · diario autonómico"
        else if (source == Province.LAS_PALMAS_BOP || source == Province.SANTA_CRUZ_BOP) "BOP · boletín provincial"
        else if (isCido(source)) "CIDO · procesos selectivos"
        else "BOP · boletín provincial"
}
