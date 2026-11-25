# OPGSim · Banco óptico

Aplicación Streamlit en español para construir un sistema óptico centrado, dibujar sus elementos y trazar haces desde el eje y los extremos de un objeto.

## Ejecutar

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

Abre la dirección local que muestra Streamlit. En este proyecto las dependencias están en `requirements.txt`.

## Uso

Para aprender el procedimiento con papel y regla, consulta la [guía paso a paso de trazado manual](docs/guia-trazado-manual.md), con dibujos de lente convergente y espejo cóncavo, ejemplos resueltos y generalización a varios elementos.

1. Define la distancia negativa del objeto, su altura y si está sobre el eje o centrado.
2. Define la abertura inicial y la longitud de onda.
3. Añade elementos y edita posiciones relativas, diámetros, grosores, índices y radios en la tabla. Elimina elementos con el selector inferior. Hay ejemplos en la barra lateral.
4. Elige trazado paraxial o exacto e inspecciona la disposición, los parámetros y la tabla de rayos. Oculta trayectorias desde la leyenda: se ocultan juntas sus prolongaciones y marcas de bloqueo. No se dibujan flechas. Las gráficas permiten zoom y exportación de imágenes; la configuración se descarga en JSON.

En **Origen de los rayos** puedes conservar el objeto finito o elegir:

- **Paralelos desde infinito:** haz axial con alturas distribuidas por la abertura admitida. La imagen paraxial está en F′; en sistemas afocales permanece en infinito. Se recalculan el stop y las pupilas para esta iluminación, sin simular el infinito mediante una distancia muy grande.
- **Desde el foco F:** usa el foco anterior del sistema completo y genera un abanico cuya salida paraxial es paralela al eje. Si F no está antes de la abertura inicial, se representa el haz incidente dirigido hacia F como construcción equivalente en el espacio objeto. Los sistemas afocales muestran un aviso porque no tienen F finito.

Ambas opciones usan el número de rayos del haz y funcionan con los dos modelos. En modo exacto pueden aparecer aberraciones y recorte en los bordes. La altura y distancia del objeto finito quedan desactivadas; el aumento transversal no se aplica a estos modos axiales. El JSON incluye el modo de iluminación.

El modelo inicial es **Exacto · Snell y reflexión**: los cambios de dirección ocurren en las intersecciones con las superficies reales. El modo paraxial permanece disponible para comparar y actúa en los planos de vértice. Las monturas y los bordes pueden bloquear rayos; esos bloqueos no son refracciones.

El modelo **Paraxial · lente delgada** concentra la potencia en un solo plano por lente, en su posición x. Usa el diámetro indicado y omite el grosor al calcular las trayectorias, las focales y la matriz. Por ejemplo, dos biconvexas de índice 1,5 y radios ±50 mm y ±20 mm, separadas 70 mm, dan salida paralela en este modelo al elegir **Paralelos desde infinito**.

En «Tipo de elemento» también puedes añadir una **Lente delgada convergente** o **Lente delgada divergente** e introducir el módulo de su focal imagen. El tipo determina el signo de f′. Estas lentes ideales ocupan un único plano y se pueden combinar con lentes gruesas en cualquiera de los modelos.

El apartado **Equivalente matricial del sistema** permite seleccionar el recorrido completo o un elemento aislado, introducir altura y ángulo, y consultar la matriz ABCD, el vector de salida y las matrices de cada paso. Usa `(y, θ)` y convierte desde el estado interno `(y, nθ)`. La altura transversal se llama y para no confundirla con la posición longitudinal x. Los ángulos de retorno siguen el sentido local de propagación; las matrices no incluyen las aberraciones del trazado exacto.

El índice de nuevos elementos es 1 por petición: en aire no produce refracción. Los ejemplos usan 1,5. Los radios predefinidos tienen sus signos asignados por la forma; el tipo personalizado conserva los signos introducidos. El menisco puede ser convergente o divergente según los radios.

## Portal de ejercicios

El botón **Abrir portal de ejercicios**, debajo del título, abre el taller. El alumno elige de uno a tres elementos y pulsa **Generar ejercicio**. Se toman lentes y espejos del catálogo de ejemplos y se varían sus diámetros, grosores y radios. Los bancos generados se comprueban para que los rayos solicitados atraviesen el montaje. No hay diafragmas; se usa como máximo un espejo, al final, para que todos los elementos participen en el recorrido.

El taller pide **chief, paralelo al eje y focal**, todos desde el mismo extremo O. El chief se apunta numéricamente al centro de la cara limitante y el focal hacia F del sistema. Se aplica Snell en cada cara; en el modelo exacto, la aberración puede impedir que el focal salga perfectamente paralelo. Cada elemento incluye su distancia focal en el enunciado. En el taller, el primer elemento fija x=0. En el banco principal, todos los elementos admiten coordenadas con signo. El objeto y el diafragma de apertura tienen posiciones independientes en el mismo eje. El diafragma puede colocarse antes, entre o después de los elementos; su diámetro y posición intervienen en el trazado y en la determinación de la abertura limitante.

El enunciado proporciona posiciones, altura de objeto, índices y radios firmados. En el canvas se colocan O y los elementos con clics sobre el eje. Luego se selecciona un tipo de rayo y se marcan inicio e interacciones; el doble clic fija el final. Un segmento provisional sigue al ratón con coordenadas y ángulo. Hay ajuste a las superficies, zoom, deshacer, borrar rayo y controles de teclado. El canvas comienza solo con la cuadrícula y el eje: no muestra referencias F/H, el centro del stop ni marcas de corrección. El alumno coloca todos los objetos ópticos. La escala vertical se amplía para facilitar el dibujo, pero las medidas se calculan en coordenadas físicas.

**He terminado · revisar ejercicio** comprueba posiciones, tipo de rayo, número y posición de interacciones, y direcciones mediante Snell y reflexión exactos. La revisión acepta errores de clic de 2 mm y errores angulares de 2°, y explica qué se ha dibujado, qué se esperaba y cómo corregirlo. Primero se revisa la colocación y después el primer error de cada rayo, para evitar una cadena de avisos causada por un único fallo. Las correcciones se muestran debajo del canvas. La solución completa permanece en Python: no se envían sus polilíneas al canvas. Los resultados son una ayuda de aprendizaje con tolerancias, no una evaluación formal. El ejercicio se conserva durante la sesión al volver al banco y regresar al taller; generar otro reinicia la construcción.

## Modelo y convenciones ópticas

Distancias en mm, ángulos en radianes, estado paraxial del rayo `(y, nu)`, con `u≈θ≈tan θ`. Propagación `[[1,d/n],[0,1]]`; superficie refractiva `[[1,0],[-(n₂−n₁)/R,1]]`. Las lentes son gruesas, con dos superficies y aire exterior. El centro de curvatura a la derecha implica radio positivo. Todos los elementos están centrados; altura significa diámetro útil. No se modelan descentramientos, inclinaciones, difracción o pérdidas de Fresnel. El modo exacto sí puede mostrar aberraciones geométricas meridionales.

En un montaje centrado, los espejos reflejan hacia atrás y los rayos vuelven a atravesar las lentes anteriores. La referencia gaussiana compone las matrices sobre ese recorrido desplegado. Para un montaje plegado, edita **Posición y**, **Giro** e **Invertir cara reflectora** en la tabla o en el formulario. El giro positivo es antihorario en el plano del dibujo. La cara activa mira hacia −x local por defecto; al invertirla mira hacia +x local y se voltea también el perfil de un espejo curvo. Un rayo que incide en el reverso se bloquea.

Los montajes fuera de eje activan el trazado exacto y muestrean el haz en la abertura inicial, que actúa durante el primer cruce. Las lentes, los espejos y sus bordes giran alrededor del vértice indicado. Los focos y matrices gaussianas del conjunto se calculan para montajes centrados. Mantén separados los perfiles físicos de los elementos.

El selector incluye espejos hiperbólicos cóncavos y parabólicos, con y sin abertura central. Introduce el radio de vértice y el diámetro exterior. El parabólico usa K = −1 y el hiperbólico permite elegir K < −1. En la versión perforada, el diámetro interior debe ser menor que el exterior. Los rayos que pasan por el hueco continúan hasta el siguiente elemento. Los cuatro tipos admiten giro e inversión de la cara reflectora. Los modelos con abertura central usan el trazado exacto, ya que el rayo axial puede seguir un recorrido diferente al de los rayos que inciden en el anillo.

Como ejemplo newtoniano, usa una abertura inicial de 40 mm y rayos paralelos desde infinito. Coloca un espejo cóncavo de radio 200 mm y diámetro 40 mm en (500, 0). Coloca un espejo plano de diámetro 12 mm en (425, 0), con giro de +45° y cara reflectora invertida. El haz de retorno se desvía hacia +y. Un ocular delgado de focal 25 mm y diámetro 20 mm en (425, 50), girado +90°, recibe ese haz. El secundario produce una obstrucción central en la entrada.

La abertura inicial es un diafragma físico de referencia. Con **Estimar automáticamente el AS** marcado, el motor elige la abertura que limita el haz axial. Al desmarcarlo, utiliza como AS el diafragma de la barra lateral y calcula las pupilas como imágenes de ese diafragma. Las demás aberturas siguen interceptando rayos en ambos modos. Por eso la pupila de entrada efectiva puede diferir de la abertura inicial. El viñeteo fuera del eje se obtiene intersectando los intervalos angulares permitidos por todas las aberturas. En modo paraxial, las aperturas se comprueban en los planos de vértice. En modo exacto, se calculan intersecciones con las superficies esféricas, refracción vectorial de Snell, reflexión especular y reflexión interna total; también se comprueban las monturas y los bordes. No hay división de intensidad por Fresnel. Las superficies deben estar separadas físicamente.

Si `M=[[A,B],[C,D]]`, la focal efectiva en aire es `−1/C`, el foco posterior desde el último vértice es `−A/C`. Las distancias de salida se miden siguiendo el sentido de propagación. Una imagen de un plano de entrada está a `−B/D` del plano de salida y su aumento es `det(M)/D`. Valores singulares se presentan como infinito, sin dividir por cero. El número f mostrado es nominal; no es el número f de trabajo a conjugado finito.

La dispersión opcional es Cauchy, anclada a 550 nm: `n(λ)=n₅₅₀+B(λ⁻²−0.55⁻²)`, λ en µm. Con B=0, cambiar la longitud de onda no modifica la trayectoria. No se incluye catálogo de materiales. El trazado exacto puede mostrar aberraciones: O′ se calcula a partir de los rayos exactos mostrados, minimizando su dispersión transversal; la tabla indica su radio RMS. O′G, FG y F′G identifican explícitamente las referencias gaussianas. F′ en modo exacto usa el mismo criterio con un haz paralelo y el número de rayos seleccionado. No se fuerzan cruces inexistentes.


## Notación y referencias de trazado

O representa el objeto; O′, la imagen gaussiana. El objeto y los rayos físicos usan líneas continuas. La imagen, su plano y las prolongaciones virtuales usan líneas discontinuas. Fᵢ/Fᵢ′ son los focos de cada elemento aislado y F/F′ los del recorrido completo. Una posición focal no es una distancia focal: la EFL se mide desde los planos principales; la BFL, desde la última superficie óptica.

El rayo principal (chief) parte de un punto de campo y atraviesa el centro del stop. Cada punto mostrado del objeto (extremos y eje) emite su principal y sus dos marginales. La altura inicial del objeto es 5 mm. Con altura 0 mm el objeto queda sobre el eje. Todos los extremos de «Haz» y los marginales se calculan sobre el intervalo admitido por el modelo seleccionado, incluido el borde; continúan después de refractarse o reflejarse. Las pupilas mostradas son gaussianas.

Las lentes finas (por ejemplo, grosor 0,1 mm) y los radios pequeños se aceptan sin aumentarlos artificialmente. El diámetro útil se recorta al cruce de las caras o al diámetro de la esfera, y se informa del valor corregido. Dibujo, monturas y cálculo usan esa misma abertura. Las caras que se encuentran en una arista se procesan sucesivamente para conservar ambos cambios de medio.

En el taller se pueden añadir rayos auxiliares, prolongaciones virtuales discontinuas hacia atrás del último tramo y marcas manuales O′, F y F′. Las salidas divergentes se prolongan automáticamente hacia su cruce virtual usando los segmentos del alumno; este puede ajustar las prolongaciones manualmente. El criterio usa la dirección de propagación, también en espejos, y no solo el signo del ángulo. La aplicación no revela soluciones precalculadas. Para hallar un foco se trazan auxiliares incidentes paralelos, mientras que el haz desde O determina la imagen. Estas construcciones se conservan, se pueden borrar y no cuentan como interacciones de los rayos evaluados.

El banco muestra inicialmente el principal, los marginales, el paralelo al eje y el focal. El haz se puede añadir en el selector. Los rayos coincidentes comparten trayectoria y sus nombres se agrupan en la leyenda.

El objeto del banco puede situarse por encima o por debajo del eje, o centrado simétricamente; su altura indica siempre el tamaño total.

En el taller, «Aproximación de lente delgada» está activada por defecto: cada lente se representa en un solo plano, con potencia (n−1)(1/R₁−1/R₂), y los espejos se tratan paraxialmente en su vértice. Al desactivarla se recuperan las dos caras, el espesor y Snell/reflexión exactos. Cambiar el modelo reinicia el dibujo; el enunciado, las focales y la corrección usan siempre el modelo activo.

Referencia del modelo de lente delgada: [OpenStax, Thin Lenses](https://openstax.org/books/university-physics-volume-3/pages/2-4-thin-lenses).

Convenio para lentes en aire: la matriz usa la focal imagen f′, con θ_salida = θ_entrada − y/f′. Si f = HF es la focal objeto cartesiana, f = −f′ y la expresión equivalente es θ_salida = θ_entrada + y/f. Las focales de espejos se expresan en el recorrido reflejado, sin identificar su signo con una distancia cartesiana sobre el eje global.
