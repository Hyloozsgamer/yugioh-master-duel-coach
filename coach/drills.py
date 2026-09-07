"""
8 Competitive Master-Tier Drills for Yu-Gi-Oh! Master Duel Coaching.
Passcodes y datos técnicos verificados contra la base de datos oficial.
"""

from typing import Dict, Any, List

DRILLS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "title": "Drill 1/8: Secuenciación Inicial y Baiting de Handtraps",
        "focus": "Snake-Eye Sinful Spoils — Turno 1 (Protección de Invocación Normal)",
        "hand": [
            "WANTED: Seeker of Sinful Spoils",
            "Snake-Eye Ash",
            "Bonfire",
            "Called by the Grave",
            "Infinite Impermanence"
        ],
        "question": "¿Cuál es la primera acción que ejecutas en el cliente para maximizar EV contra Ash Blossom / Droll?",
        "options": [
            "A) Activar Bonfire para añadir Snake-Eye Poplar y forzar Ash Blossom.",
            "B) Activar WANTED: Seeker of Sinful Spoils para buscar Diabellstar primero.",
            "C) Invocación Normal directa de Snake-Eye Ash para buscar Poplar.",
            "D) Colocar Called by the Grave y pasar turno sin cometer sobreextensión."
        ],
        "correct_option": "B",
        "best_line_title": "Línea Segura con WANTED (EV Máximo)",
        "line_type": "Segura y de Máximo Valor (EV)",
        "analysis": "WANTED te permite buscar a Diabellstar sin consumir tu Invocación Normal. Si el rival usa Ash Blossom sobre WANTED, agota su interacción en un motor accesorio, dejándote limpia la Invocación Normal de Snake-Eye Ash y el Bonfire. Si resuelve, Diabellstar coloca Original Sinful Spoils directo al campo desde el Deck, lo cual NO añade a la mano y por tanto NO activa la ventana de Droll & Lock Bird.",
        "steps": [
            {
                "step": 1,
                "action": "ACTIVAR MAGIA DE JUEGO RÁPIDO",
                "card_name": "WANTED: Seeker of Sinful Spoils",
                "card_es": "SE BUSCA: Buscadora de Botín del Pecado",
                "passcode": 80845034,
                "where": "Mano",
                "inputs": [
                    "Pulsar WANTED: Seeker of Sinful Spoils en mano",
                    "Elegir [Activar]",
                    "Target: Seleccionar 'Diabellstar the Black Witch' desde el Deck",
                    "Confirmar búsqueda en cliente"
                ],
                "result": "Diabellstar the Black Witch añadida a la mano; WANTED al Cementerio.",
                "timing": "Main Phase 1, Turno 1. Open Game State.",
                "chain_notes": "Si el rival activa Ash Blossom (CL2), NO encadenes Called by the Grave. Guarda Called para Maxx 'C' o Nibiru, ya que conservas Bonfire y Normal Summon de Snake-Eye Ash como líneas completas intactas."
            },
            {
                "step": 2,
                "action": "INVOCACIÓN ESPECIAL DESDE MANO",
                "card_name": "Diabellstar the Black Witch",
                "card_es": "Diabellstar la Bruja Negra",
                "passcode": 72270339,
                "where": "Mano -> Main Monster Zone 3",
                "inputs": [
                    "Pulsar Diabellstar en la mano",
                    "Elegir [Invocación Especial]",
                    "Coste: Seleccionar y enviar Infinite Impermanence al Cementerio (o carta prescindible)",
                    "Confirmar zona MM3",
                    "Al entrar: Activar Trigger CL1 de Diabellstar para Colocar 'Original Sinful Spoils - Snake-Eye' en S/T 3"
                ],
                "result": "Diabellstar (2500 ATK) en campo; Original Sinful Spoils colocada boca abajo.",
                "timing": "Main Phase 1. Ventana de Invocación con éxito.",
                "chain_notes": "Colocar desde el Deck no es 'añadir a la mano'; esquiva Droll & Lock Bird."
            }
        ],
        "end_board": "Diabellstar en MM3, Original Sinful Spoils en ST3, mano restante: Snake-Eye Ash, Bonfire, Called by the Grave intacta.",
        "follow_up": "Snake-Eye Flamberge Dragon en GY para revivir 2 monstruos de nivel 1 en el turno del oponente.",
        "plan_b": "Si niegan a Diabellstar con Infinite Impermanence: Normal Summon de Snake-Eye Ash y continúa la línea completa.",
        "principle": "Bait con motores auxiliares antes de comprometer la Invocación Normal."
    },
    {
        "id": 2,
        "title": "Drill 2/8: Gestión de Invocaciones bajo la Regla de las 5 (Nibiru Timing)",
        "focus": "Conteo de Invocaciones y Protección de Board",
        "hand": ["Snake-Eye Ash", "Snake-Eye Poplar", "Bonfire"],
        "question": "¿En qué momento exacto debes consolidar tu seguro contra Nibiru, the Primal Being?",
        "options": [
            "A) En la invocación 4, trayendo Apollousa o enviando Promethean Princess al GY.",
            "B) Ignorar el contador y continuar hasta 10 invocaciones sin negadores.",
            "C) Detener el turno en la invocación 3 con sólo un monstruo de 1000 ATK.",
            "D) Sacrificar todo el campo voluntariamente antes de la quinta invocación."
        ],
        "correct_option": "A",
        "best_line_title": "Pivote Seguro en Invocación 4",
        "line_type": "Segura contra Handtraps de Alto Impacto",
        "analysis": "Nibiru se activa en la 5ta invocación del turno. Si configuras a Promethean Princess en el Cementerio o Apollousa antes o exactamente en la 5ta invocación, la activación de Nibiru se convierte en un intercambio favorable o es anulada de raíz.",
        "steps": [
            {
                "step": 1,
                "action": "CONFIGURAR TRIGGER EN CEMENTERIO",
                "card_name": "Promethean Princess, Bestower of Flames",
                "card_es": "Princesa Prometeica, Dispensadora de Llamas",
                "passcode": 60461804,
                "where": "Extra Monster Zone -> Cementerio",
                "inputs": [
                    "Invocar Link a Promethean Princess usando 2 monstruos de FUEGO",
                    "Usar su efecto de revivir",
                    "Vincularla inmediatamente a un Link-4 (ej. Apollousa o Amblowhale) para mandarla al GY"
                ],
                "result": "Promethean Princess reside en GY lista para interrumpir en respuesta a cualquier invocación rival.",
                "timing": "Invocación 4 del turno.",
                "chain_notes": "Si el rival lanza Nibiru tras la invocación 5, el tributo enviará a Flamberge al GY, activando su efecto de revivir a 2 monstruos y Princess sigue viva en GY."
            }
        ],
        "end_board": "Apollousa (3 materiales) o Flamberge Dragon con Promethean Princess en GY.",
        "follow_up": "I:P Masquerena en campo para invocar S:P Little Knight en el turno del oponente.",
        "plan_b": "Si cae Nibiru: Trigger de Flamberge en GY revive a Snake-Eye Ash y Poplar; reconstruye en Link-2.",
        "principle": "Nunca cruces la Invocación 5 sin un negador de monstruos o un disparador de GY activo."
    },
    {
        "id": 3,
        "title": "Drill 3/8: Mitigación de Daño bajo Maxx 'C'",
        "focus": "Control de Recursos y Breakpoints de Invocación",
        "hand": ["Snake-Eye Ash", "Called by the Grave", "Ash Blossom & Joyous Spring"],
        "question": "Activas Snake-Eye Ash. El rival responde con Maxx 'C' (CL2). Tienes Called by the Grave en mano. ¿Cuál es la jugada con mayor EV?",
        "options": [
            "A) Encadenar Called by the Grave (CL3) desterrando Maxx 'C'.",
            "B) Dejar resolver Maxx 'C' para guardar Called by the Grave para el turno rival.",
            "C) Rendirse inmediatamente para no dar información.",
            "D) Realizar 6 Invocaciones Especiales para intentar deckear al rival."
        ],
        "correct_option": "A",
        "best_line_title": "Anulación Directa de Maxx 'C' con Retención de Turno",
        "line_type": "Máximo Valor (EV)",
        "analysis": "Maxx 'C' es la carta más definitoria del formato Master Duel. Permitir que resuelva le da al rival +4 a +8 cartas si continúas, o te obliga a pasar con un campo insignificante. Neutralizarla con Called by the Grave asegura tu turno completo con 0 cartas extra para el rival.",
        "steps": [
            {
                "step": 1,
                "action": "ACTIVAR MAGIA DE JUEGO RÁPIDO EN CADENA",
                "card_name": "Called by the Grave",
                "card_es": "Llamado por la Tumba",
                "passcode": 24224830,
                "where": "Mano (CL3)",
                "inputs": [
                    "Seleccionar [Activar en Cadena]",
                    "Target: Seleccionar 'Maxx \"C\"' en el Cementerio del rival",
                    "Confirmar resolución"
                ],
                "result": "Maxx 'C' desterrada; sus efectos y los de cualquier otra copia quedan negados hasta el final del próximo turno.",
                "timing": "Cadena: CL1 Ash -> CL2 Maxx 'C' -> CL3 Called by the Grave.",
                "chain_notes": "Called by the Grave también niega copias adicionales de Maxx 'C' que el rival pudiera tener en mano."
            }
        ],
        "end_board": "End board completo estándar sin regalar recursos.",
        "follow_up": "Control de tablero y negaciones múltiples.",
        "plan_b": "Si el rival tiene Ghost Belle contra Called: Pasar de inmediato en Bagger (dar 1 solo robo) con Poplar colocado en S/T.",
        "principle": "Maxx 'C' siempre es el target número 1 prioritario para Called by the Grave o Crossout Designator."
    },
    {
        "id": 4,
        "title": "Drill 4/8: Interacción y Ventana de Droll & Lock Bird",
        "focus": "Manejo de Ventanas de Búsqueda y Colocación Directa",
        "hand": ["Bonfire", "Snake-Eye Poplar", "Original Sinful Spoils - Snake-Eye"],
        "question": "¿Cómo se evita el cierre de turno si el rival activa Droll & Lock Bird tras tu primera búsqueda?",
        "options": [
            "A) Empleando cartas que 'Invocan desde el Deck' o 'Colocan en Campo' en lugar de 'Añadir a la mano'.",
            "B) Activando cartas de robo para intentar superar a Droll.",
            "C) Esperar a la Battle Phase para buscar.",
            "D) Usar Efecto Rápido de robo en cadena a Droll."
        ],
        "correct_option": "A",
        "best_line_title": "Línea de Desvío Directo Campo/Cementerio",
        "line_type": "Adaptativa / Anti-Floodgate",
        "analysis": "Droll & Lock Bird solo impide 'añadir cartas desde el Deck a la mano'. No restringe invocar directamente desde el Deck (Original Sinful Spoils) ni colocar cartas directamente en zonas de Magias/Trampas (Diabellstar, Poplar).",
        "steps": [
            {
                "step": 1,
                "action": "ACTIVAR MAGIA NORMAL",
                "card_name": "Original Sinful Spoils - Snake-Eye",
                "card_es": "Botín del Pecado Original - Ojos de Serpiente",
                "passcode": 45458027,
                "where": "Mano o Campo",
                "inputs": [
                    "Mandar 1 carta boca arriba al GY como coste",
                    "Invocar Especialmente 1 monstruo FUEGO Nivel 1 directamente desde el Deck",
                    "Seleccionar Zona MM3"
                ],
                "result": "Monstruo en campo legalmente bajo efecto activo de Droll & Lock Bird.",
                "timing": "Main Phase 1.",
                "chain_notes": "Legal al 100% bajo Droll porque es Invocación Especial, no búsqueda."
            }
        ],
        "end_board": "Promethean Princess en GY + Flamberge Dragon en campo.",
        "follow_up": "Invocación en Standby Phase del rival.",
        "plan_b": "Si cortan la Invocación Especial: Establecer monstruos en modo de defensa y setear Infinite Impermanence.",
        "principle": "Aprende la distinción técnica entre 'Añadir a la mano', 'Colocar' e 'Invocar del Deck'."
    },
    {
        "id": 5,
        "title": "Drill 5/8: Going Second — Breakpoints y Chain Blocking",
        "focus": "Protección de Efectos Críticos en Cadena (Turno 2)",
        "hand": ["Snake-Eye Poplar", "Snake-Eye Flamberge Dragon", "Super Polymerization"],
        "question": "Al invocar por Enlace usando Poplar y otro monstruo, tienes 2 efectos Trigger simultáneos. ¿Cómo ordenas la cadena para proteger a tu starter principal?",
        "options": [
            "A) CL1 Efecto del monstruo Link, CL2 Poplar (para colocar en S/T).",
            "B) CL1 Poplar, CL2 Efecto del monstruo Link.",
            "C) Declarar solo un efecto y renunciar al segundo.",
            "D) Activar una magia rápida en CL1."
        ],
        "correct_option": "B",
        "best_line_title": "Chain Blocking Óptimo de Enlace",
        "line_type": "Técnica de Bloqueo de Cadena",
        "analysis": "El efecto más importante debe colocarse en CL1, y el efecto secundario en CL2. De este modo, el rival sólo puede responder directamente a CL2 con cartas como Ash Blossom o Baronne de Fleur, protegiendo al efecto de CL1 de cualquier negación directa.",
        "steps": [
            {
                "step": 1,
                "action": "ORDENAR TRIGGERS SEGÚN SEGOC",
                "card_name": "Snake-Eye Poplar",
                "card_es": "Álamo Ojos de Serpiente",
                "passcode": 63995874,
                "where": "Cementerio / Campo",
                "inputs": [
                    "En la ventana de selección de cadena: Seleccionar Poplar como CL1",
                    "Seleccionar el monstruo Link secundario como CL2",
                    "Confirmar orden de cadena"
                ],
                "result": "CL2 protege a CL1 frente a respuestas del adversario.",
                "timing": "Ventana Trigger post-Invocación.",
                "chain_notes": "Si el rival tiene Baronne de Fleur, se verá obligado a gastar su negación en CL2 o dejar pasar ambos."
            }
        ],
        "end_board": "Tablero rival roto, recursos en S/T colocados.",
        "follow_up": "Empuje a daño letal en Battle Phase.",
        "plan_b": "Si el rival no responde: Ambos efectos resuelven en orden inverso con éxito total.",
        "principle": "El efecto indispensable siempre va en CL1 con un escudo en CL2."
    },
    {
        "id": 6,
        "title": "Drill 6/8: Bucle de Recursos y Grind Game en Cementerio",
        "focus": "Reciclaje Infinito de Ventajas y Triggers de Cementerio",
        "hand": ["Snake-Eye Flamberge Dragon en Campo", "Promethean Princess en GY"],
        "question": "En el turno del oponente, ¿cuándo debes activar el efecto de Flamberge para colocar un monstruo en la zona de Magia/Trampa?",
        "options": [
            "A) En la Draw Phase inmediatamente.",
            "B) En respuesta a la Invocación del monstruo clave del rival o antes de que entre a Battle Phase.",
            "C) Esperar a la End Phase sin interrumpir.",
            "D) Activarlo en cadena a tu propia carta."
        ],
        "correct_option": "B",
        "best_line_title": "Interrupción Quirúrgica de Tempo",
        "line_type": "Control de Tiempo y Ventaja",
        "analysis": "Colocar el monstruo rival en su propia zona de S/T desactiva sus materiales de Invocación Extra Deck y le resta espacio para Magias y Trampas. Hacerlo en el momento en que declara su jugada principal rompe su línea de combo.",
        "steps": [
            {
                "step": 1,
                "action": "ACTIVAR EFECTO RÁPIDO DE MONSTRUO",
                "card_name": "Snake-Eye Flamberge Dragon",
                "card_es": "Dragón Flamberge Ojos de Serpiente",
                "passcode": 91706607,
                "where": "Main Monster Zone 3",
                "inputs": [
                    "Pulsar Flamberge Dragon en campo",
                    "Target: 1 monstruo boca arriba en el campo o GY del rival",
                    "Colocarlo como Magia Continua boca arriba en su zona S/T"
                ],
                "result": "Monstruo rival neutralizado y zona S/T ocupada.",
                "timing": "Main Phase rival, en resolución de jugada.",
                "chain_notes": "No destruye, por lo que evade efectos flotantes de destrucción."
            }
        ],
        "end_board": "Campo rival bloqueado; Princess lista en GY para destruir si invocan de nuevo.",
        "follow_up": "Recuperar 2 monstruos al ir Flamberge al GY.",
        "plan_b": "Si niegan con Called by the Grave: Encadenar Promethean Princess desde GY si hay fuego en campo.",
        "principle": "El removal que no destruye ni envía al GY es el más difícil de recuperar para el rival."
    },
    {
        "id": 7,
        "title": "Drill 7/8: Disciplina de Columnas y Gestión de S/T",
        "focus": "Ubicación en Zonas frente a Infinite Impermanence",
        "hand": ["Original Sinful Spoils", "Called by the Grave"],
        "question": "Al colocar y activar Magias/Trampas en campo, ¿en qué columna NUNCA debes activar una Magia continua o importante?",
        "options": [
            "A) En la misma columna donde el rival tiene una carta Colocada (posible Infinite Impermanence).",
            "B) En la columna central siempre.",
            "C) En las columnas de los extremos.",
            "D) Da igual la columna en Master Duel."
        ],
        "correct_option": "A",
        "best_line_title": "Disciplina de Zonas Anti-Impermanence",
        "line_type": "Hábito Mecánico Competitivo",
        "analysis": "Si el rival activa una Infinite Impermanence colocada, niega todos los efectos de Magias y Trampas en esa misma columna durante el resto del turno. Activar tus cartas en columnas limpias previene autoinvalidar tus jugadas.",
        "steps": [
            {
                "step": 1,
                "action": "SELECCIÓN CONSCIENTE DE ZONA EN CLIENTE",
                "card_name": "Infinite Impermanence",
                "card_es": "Impermanencia Infinita",
                "passcode": 10045474,
                "where": "Zona S/T",
                "inputs": [
                    "Inspeccionar las zonas S/T 1-5 del oponente",
                    "Identificar cartas boca abajo",
                    "Colocar tus cartas en columnas donde el rival NO tenga cartas seteadas"
                ],
                "result": "Inmunidad a la anulación de columna de Impermanence.",
                "timing": "En cada colocación de carta en Master Duel.",
                "chain_notes": "Activar en opciones del juego: 'Ubicación manual de cartas' para evitar que el juego las coloque automáticamente en columnas peligrosas."
            }
        ],
        "end_board": "Columnas limpias y efectos seguros.",
        "follow_up": "Garantía de resolución de Magias Continuas y de Campo.",
        "plan_b": "Si caes en columna de Impermanence: No actives más cartas en esa columna hasta el próximo turno.",
        "principle": "La columna en la que juegas tus cartas en Yu-Gi-Oh! moderno es tan relevante como la carta misma."
    },
    {
        "id": 8,
        "title": "Drill 8/8: Cierre de Partida — Cálculo de Daño Letal bajo Interrupciones",
        "focus": "Cálculo Matemático de Daño Letal (OTK)",
        "hand": ["Accesscode Talker en Extra Deck", "Amphibious Swarmship Amblowhale en GY"],
        "question": "Tienes 5300 de daño en mesa y el rival tiene 6500 LP con 1 monstruo en defensa (1500 DEF). ¿Qué Link-4 debes construir para garantizar letal exacto?",
        "options": [
            "A) Accesscode Talker usando un Link-3 como material (ganando 3000 ATK -> 5300 ATK total) + limpieza de campo.",
            "B) Apollousa de 4 materiales para atacar.",
            "C) Pasar a End Phase y esperar al siguiente turno.",
            "D) Invocar un Link-2 defensivo."
        ],
        "correct_option": "A",
        "best_line_title": "Secuencia Letal de Accesscode Talker",
        "line_type": "Línea de Daño Máximo y Fin de Duelo",
        "analysis": "Accesscode Talker con material Link-3 alcanza 5300 ATK y destruye cartas del rival desterrando enlaces de atributos distintos de tu GY sin que el rival pueda encadenar efectos. Al limpiar el monstruo en defensa, 5300 + otro atacante en campo supera ampliamente los 6500 LP.",
        "steps": [
            {
                "step": 1,
                "action": "INVOCACIÓN POR ENLACE - 4",
                "card_name": "Accesscode Talker",
                "card_es": "Hablador de Código de Acceso",
                "passcode": 86066372,
                "where": "Extra Deck -> Extra Monster Zone",
                "inputs": [
                    "Seleccionar Invocación Link",
                    "Materiales: Promethean Princess (Link-3) + 1 monstruo",
                    "Efecto al entrar (CL1): Aumentar ATK en 3000 (total 5300 ATK)",
                    "Efecto Ignition: Desterrar 1 Link del GY para destruir el monstruo rival (sin respuesta del oponente)"
                ],
                "result": "Accesscode Talker con 5300 ATK; campo rival limpio.",
                "timing": "Main Phase 1, Turno 2 o 3.",
                "chain_notes": "El rival no puede activar cartas o efectos en respuesta a la activación de los efectos de Accesscode Talker."
            }
        ],
        "end_board": "Accesscode Talker (5300 ATK) + atacante secundario. Ataque directo: 8000+ daño.",
        "follow_up": "Victoria por daño a LP.",
        "plan_b": "Si el rival tiene efecto rápido antes de la invocación: Forzarlo antes de comprometer los materiales finales.",
        "principle": "En turno de matar, calcula el daño letal exacto considerando limpieza de campo sin respuesta."
    }
]
