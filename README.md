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

El apartado **Equivalente matricial del sistema** permite seleccionar el recorrido completo o un elemento aislado, introducir altura y ángulo, y consultar la matriz ABCD, el vector de salida y las matrices de cada paso. Usa `(y, θ)` y convierte desde el estado interno `(y, nθ)`. La altura transversal se llama y para no confundirla con la posición longitudinal x. Los ángulos de retorno siguen el sentido local de propagación; las matrices no incluyen las aberraciones del trazado exacto.

El índice de nuevos elementos es 1 por petición: en aire no produce refracción. Los ejemplos usan 1,5. Los radios predefinidos tienen sus signos asignados por la forma; el tipo personalizado conserva los signos introducidos. El menisco puede ser convergente o divergente según los radios.

## Portal de ejercicios

El botón **Abrir portal de ejercicios**, debajo del título, abre el taller. El alumno elige de uno a tres elementos y pulsa **Generar ejercicio**. Se toman lentes y espejos del catálogo de ejemplos y se varían sus diámetros, grosores y radios. Los bancos generados se comprueban para que los rayos solicitados atraviesen el montaje. No hay diafragmas; se usa como máximo un espejo, al final, para que todos los elementos participen en el recorrido.

El taller pide el **chief y los marginales**: el chief se apunta numéricamente al centro de la cara limitante; los marginales parten del mismo extremo O que el chief y continúan tras alcanzar los bordes útiles del haz de ese punto.

El enunciado proporciona posiciones, altura de objeto, índices y radios firmados. En el canvas se colocan O y los elementos con clics sobre el eje. Luego se selecciona un tipo de rayo y se marcan inicio e interacciones; el doble clic fija el final. Un segmento provisional sigue al ratón con coordenadas y ángulo. Hay ajuste a las superficies, zoom, deshacer, borrar rayo y controles de teclado. El canvas comienza solo con la cuadrícula y el eje: no muestra referencias F/H, el centro del stop ni marcas de corrección. El alumno coloca todos los objetos ópticos. La escala vertical se amplía para facilitar el dibujo, pero las medidas se calculan en coordenadas físicas.

**He terminado · revisar ejercicio** comprueba posiciones, tipo de rayo, número y posición de interacciones, y direcciones mediante Snell y reflexión exactos. La revisión acepta errores de clic de 2 mm y errores angulares de 2°, y explica qué se ha dibujado, qué se esperaba y cómo corregirlo. Primero se revisa la colocación y después el primer error de cada rayo, para evitar una cadena de avisos causada por un único fallo. Las correcciones se muestran debajo del canvas. La solución completa permanece en Python: no se envían sus polilíneas al canvas. Los resultados son una ayuda de aprendizaje con tolerancias, no una evaluación formal. El ejercicio se conserva durante la sesión al volver al banco y regresar al taller; generar otro reinicia la construcción.

## Modelo y convenciones ópticas

Distancias en mm, ángulos en radianes, estado paraxial del rayo `(y, nu)`, con `u≈θ≈tan θ`. Propagación `[[1,d/n],[0,1]]`; superficie refractiva `[[1,0],[-(n₂−n₁)/R,1]]`. Las lentes son gruesas, con dos superficies y aire exterior. El centro de curvatura a la derecha implica radio positivo. Todos los elementos están centrados; altura significa diámetro útil. No se modelan descentramientos, inclinaciones, difracción o pérdidas de Fresnel. El modo exacto sí puede mostrar aberraciones geométricas meridionales.

Los espejos reflejan hacia atrás en coordenadas físicas. El trazado vuelve a atravesar las lentes anteriores; no alcanza los elementos situados detrás del primer espejo en un montaje centrado. Internamente, las matrices gaussianas se componen sobre el recorrido axial desplegado y las posiciones se convierten de nuevo a coordenadas físicas. El grosor de espejo no modifica el modelo; el de diafragma introduce dos aberturas y paredes opacas.

La abertura inicial es un diafragma físico de referencia. El motor identifica la abertura que limita el ángulo del haz desde el punto axial del objeto a su distancia actual. Calcula las pupilas como imágenes de esa abertura a través de la óptica anterior y posterior. Por eso la pupila de entrada efectiva puede diferir de la abertura inicial. El viñeteo fuera del eje se obtiene intersectando los intervalos angulares permitidos por todas las aberturas. En modo paraxial, las aperturas se comprueban en los planos de vértice. En modo exacto, se calculan intersecciones con las superficies esféricas, refracción vectorial de Snell, reflexión especular y reflexión interna total; también se comprueban las monturas y los bordes. No hay división de intensidad por Fresnel. Las superficies deben estar separadas físicamente.

Si `M=[[A,B],[C,D]]`, la focal efectiva en aire es `−1/C`, el foco posterior desde el último vértice es `−A/C`. Las distancias de salida se miden siguiendo el sentido de propagación. Una imagen de un plano de entrada está a `−B/D` del plano de salida y su aumento es `det(M)/D`. Valores singulares se presentan como infinito, sin dividir por cero. El número f mostrado es nominal; no es el número f de trabajo a conjugado finito.

La dispersión opcional es Cauchy, anclada a 550 nm: `n(λ)=n₅₅₀+B(λ⁻²−0.55⁻²)`, λ en µm. Con B=0, cambiar la longitud de onda no modifica la trayectoria. No se incluye catálogo de materiales. El trazado exacto puede mostrar aberraciones: O′ se calcula a partir de los rayos exactos mostrados, minimizando su dispersión transversal; la tabla indica su radio RMS. O′G, FG y F′G identifican explícitamente las referencias gaussianas. F′ en modo exacto usa el mismo criterio con un haz paralelo y el número de rayos seleccionado. No se fuerzan cruces inexistentes.


## Notación y referencias de trazado

O representa el objeto; O′, la imagen gaussiana. El objeto y los rayos físicos usan líneas continuas. La imagen, su plano y las prolongaciones virtuales usan líneas discontinuas. Fᵢ/Fᵢ′ son los focos de cada elemento aislado y F/F′ los del recorrido completo. Una posición focal no es una distancia focal: la EFL se mide desde los planos principales; la BFL, desde la última superficie óptica.

El rayo principal (chief) parte de un punto de campo y atraviesa el centro del stop. Cada punto mostrado del objeto (extremos y eje) emite su principal y sus dos marginales. La altura del objeto es 0 mm por defecto; se puede aumentar para ver por separado la familia del extremo y la axial. Todos los extremos de «Haz» y los marginales se calculan sobre el intervalo admitido por el modelo seleccionado, incluido el borde; continúan después de refractarse o reflejarse. Las pupilas mostradas son gaussianas.

Las lentes finas (por ejemplo, grosor 0,1 mm) y los radios pequeños se aceptan sin aumentarlos artificialmente. El diámetro útil se recorta al cruce de las caras o al diámetro de la esfera, y se informa del valor corregido. Dibujo, monturas y cálculo usan esa misma abertura. Las caras que se encuentran en una arista se procesan sucesivamente para conservar ambos cambios de medio.

En el taller se pueden añadir rayos auxiliares, prolongaciones virtuales discontinuas hacia atrás del último tramo y marcas manuales O′, F′ y Oᵥ. El alumno decide la longitud y los puntos de cruce; la aplicación no revela soluciones. Para hallar un foco se trazan auxiliares incidentes paralelos, mientras que el haz desde O determina la imagen. Estas construcciones se conservan, se pueden borrar y no cuentan como interacciones de los rayos evaluados.
