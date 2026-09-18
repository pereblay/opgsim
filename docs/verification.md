# Verificación de fórmulas y convenios

Revisión: 16 de septiembre de 2026. Alcance: `optics.py`, `raytrace.py` y su presentación en `app.py`. Se contrastaron las secciones pertinentes de los documentos, no la totalidad de las 415 páginas de `Full.pdf`.

## Resultado

Las ecuaciones de propagación, refracción, reflexión y formación de imagen implementadas son coherentes con las referencias bajo los convenios indicados abajo. No se encontró un error de signo en esas ecuaciones. Esto no certifica cualquier geometría o cualquier valor numérico posible: los resultados cardinales son de primer orden y el trazado exacto tiene las limitaciones descritas al final.

Se corrigió la cancelación numérica de la sagita para superficies casi planas; además, se distinguió la pendiente paraxial del ángulo exacto en la tabla de rayos y se corrigió una frase del README que excluía todas las aberraciones aunque el modo exacto puede mostrarlas.

## Fuentes contrastadas

- **MIL-HDBK-141, capítulo 5**, archivo aportado `ch05.pdf`: §5.2 (signos), §5.4.5 (refracción vectorial), §5.9 (ecuaciones paraxiales) y §§5.10–5.11 (diagramas paraxiales y comparación con rayos finitos). En el PDF, páginas 3, 9–10 y 32–36.
- **Schnick, Calculus-Based Physics**, archivo aportado `Full.pdf`: capítulos B26–B29, páginas PDF 334–357. El capítulo [B28 también está en LibreTexts](https://phys.libretexts.org/Bookshelves/University_Physics/Calculus-Based_Physics_%28Schnick%29/Volume_B%3A_Electricity_Magnetism_and_Optics/B28%3A_Thin_Lenses_-_Ray_Tracing): construcción con lentes delgadas y signos de las imágenes.
- [Edmund Optics, trazado paraxial](https://www.edmundoptics.com/knowledge-center/application-notes/optics/geometrical-optics-101-paraxial-ray-tracing-calculations/): ecuaciones superficie a superficie, ejemplo PCX y definición de stop, chief ray y marginal.
- [RP Photonics, matrices ABCD](https://www.rp-photonics.com/abcd_matrix.html): estado reducido y composición matricial; [pupilas de entrada y salida](https://www.rp-photonics.com/entrance_and_exit_pupil.html).
- [Physically Based Rendering, 4.ª edición, §9.3](https://www.pbr-book.org/4ed/Reflection_Models/Specular_Reflection_and_Transmission): reflexión, Snell vectorial y reflexión interna total.
- [OpenStax, espejos esféricos](https://openstax.org/books/university-physics-volume-3/pages/2-2-spherical-mirrors): foco paraxial y construcción de imágenes.

## Convenios que no deben mezclarse

1. **Coordenadas físicas:** x crece a la derecha, y hacia arriba; objeto en x<0; referencia física inicial en x=0. En lentes, R>0 significa centro de curvatura a la derecha del vértice. Una biconvexa tiene R₁>0 y R₂<0. Las formas predefinidas asignan los signos; la lente personalizada usa los introducidos.
2. **Schnick:** el radio positivo para una cara convexa es un convenio de forma. Para una lente iluminada inicialmente desde la izquierda, su segundo radio cambia de signo al convertirlo al convenio cartesiano. La suma de curvaturas de su fórmula pasa así a la diferencia `1/R₁−1/R₂`. Para una lente delgada en x=L, la distancia positiva de objeto real es `o=L−xO`; la distancia de imagen es `i=xO′−L`. Se recuperan `1/o+1/i=1/f` y `m=−i/o`.
3. **Después de reflejar:** el dibujo conserva x físico; el cálculo matricial usa una coordenada axial s que crece a lo largo del recorrido. Tras un espejo en xM, `x=2xM−s`. No hay transmisión a través del espejo ideal. El manual militar permite otra representación con índice firmado al invertir la marcha; aquí los índices materiales siguen siendo positivos y se transforma la coordenada. No se deben añadir también índices negativos a estas matrices.
4. **Ángulos:** en el cálculo paraxial `u≈θ≈tan θ`, con θ pequeño en radianes. El estado es `(y,q)` con `q=nu`. En modo exacto se usan vectores unitarios; una pendiente inicial u se convierte a ángulo mediante `atan(u)`. Incidencia y refracción exactas se miden respecto de la normal, no del eje.

## Ecuaciones verificadas

Las siguientes expresiones se derivan para los planos de referencia del programa; las distancias de salida siguen la marcha local. El exterior de las lentes y del sistema es aire con n=1.

### Propagación y superficies

```text
T(d,n) = [[1, d/n], [0, 1]]
S(n₁,n₂,R) = [[1, 0], [−(n₂−n₁)/R, 1]]
y₂ = y₁ + d q₁/n
q₂ = q₁ − y (n₂−n₁)/R
```

Una superficie plana no cambia q, pero sí cambia `u=q/n` si cambia n: una matriz identidad en esa interfaz NO significa ausencia de refracción oblicua. Con incidencia normal o índices iguales, que el rayo no se desvíe es correcto.

En el estado local desplegado, el espejo en aire tiene `C=−2/|R|` si es cóncavo, `C=+2/|R|` si es convexo y C=0 si es plano. El cambio del sentido físico se aplica aparte. Para incidencia inicial desde la izquierda, el radio cartesiano del espejo cóncavo es negativo. Su focal local es positiva, |R|/2; la del convexo es negativa.

En un retorno por una interfaz refractiva cambian simultáneamente el signo del radio local y el salto de índice, por lo que el coeficiente de refracción coincide con el de la ida; las superficies se recorren en orden inverso y con los índices de propagación correspondientes.

### Snell y reflexión exactos

Con dirección incidente unitaria d y normal unitaria N orientada contra d:

```text
reflexión: r = d − 2(d·N)N
η = n₁/n₂; c = −d·N
k = 1 − η²(1−c²)
refracción: t = ηd + (ηc−√k)N, si k≥0
reflexión interna total: k<0
```

Se comprueban vectores de módulo uno, continuidad de la componente tangencial `n₁ sin i=n₂ sin t`, reversibilidad y ambos lados del ángulo crítico. PBRT orienta su vector incidente hacia fuera de la interfaz: hay que invertirlo para compararlo con d, que aquí sigue el desplazamiento de la luz.

Las intersecciones se realizan con la esfera de centro `(xv+R,0)` y radio |R|; se descarta la semiesfera ajena a la cara seleccionada. La sagita se evalúa ahora mediante la forma racionalizada equivalente:

```text
sag(R,y) = (y/R)y / [1+√(1−(y/R)²)]
```

Esto evita restar dos cantidades casi iguales cuando |R| es muy grande.

### Focos, planos principales e imagen

Para `M=[[A,B],[C,D]]`, desde la referencia inicial hasta la final, `det(M)=1` en el estado reducido. En aire:

```text
f′ = −1/C
F = D/C                        (coordenada desde la referencia de entrada)
F′ = s_salida − A/C
H = (D−1)/C
H′ = s_salida + (1−A)/C
```

F′ y H′ se convierten a x físico si hay retorno. La BFL desde la última superficie activa incluye el desplazamiento entre esa superficie y el plano final de referencia; no debe confundirse con la EFL.

Para obtener la imagen se incluye primero el desplazamiento objeto→entrada: `Mo=M T(−xO,1)`. Con sus coeficientes, `l=−Bo/Do` y `m=det(Mo)/Do`. La condición de imagen es que el coeficiente B de `T(l,1)Mo` se anule. C=0 representa un sistema afocal; Do=0 representa imagen en infinito.

### Stop y pupilas

Para el punto axial a la distancia de objeto seleccionada, la superficie limitante minimiza `aᵢ/|Bᵢ|`, donde aᵢ es el semidiámetro y Bᵢ corresponde al recorrido objeto→superficie. No se selecciona simplemente el diafragma de menor diámetro.

Si P lleva desde la referencia inicial hasta el stop, la pupila de entrada se calcula conjugando ese plano con `P⁻¹`. Equivalentemente, su posición es `Bₚ/Aₚ` y su diámetro es `diámetro_stop/|Aₚ|`. Para la pupila de salida se conjuga el stop con `M P⁻¹`. Son imágenes del stop y pueden ser reales, virtuales o estar en infinito. La abertura física inicial puede no coincidir con la pupila de entrada efectiva.

## Comprobaciones reproducibles

Ejecutar `.venv/bin/python -m unittest discover -s tests -v` desde la raíz.

| Comprobación | Criterio |
|---|---|
| PCX de Edmund: R=26,25 mm, t=5 mm, n=1,517 | BFL≈47,48 mm; EFL=26,25/0,517 |
| Lente gruesa | Coincidencia con ecuación del fabricante con término de espesor |
| Espejo plano en x=50, objeto x=−120 | Imagen virtual x=220, aumento +1; luz reflejada hacia la izquierda |
| Espejos de radio 100 mm en x=50 | Focos físicos x=0 (cóncavo) y x=100 (convexo) |
| Pupila anterior con lente f=50 y stop a 25 o 100 mm detrás | Posición y tamaño coinciden con la ecuación de lente aplicada en sentido inverso |
| Snell con 13 orientaciones de normal y 5 incidencias | Ley de senos, reversibilidad y reflexión aplicada dos veces |
| 60 sistemas reproducibles (semilla 712) | Derivada del trazado exacto en el eje coincide con la matriz paraxial; incluye lentes múltiples y tres tipos de espejo |
| Casos singulares y representación | Imagen/pupila en infinito, recorte, doble paso, O/O′ y focos; sin flechas residuales |

La comparación de 60 sistemas usa diferencias centrales con alturas ±10⁻⁴ mm y pendientes ±10⁻⁶. Cada componente de la matriz se compara con `atol=3×10⁻⁶, rtol=10⁻⁷`; los componentes tienen unidades distintas, por lo que esa tolerancia no es un error global en milímetros. Es una prueba del límite paraxial, no de la calidad de imagen a gran abertura.

## Límites de interpretación

- O′, F/F′, planos principales y pupilas siguen siendo gaussianos en ambos modos. Los rayos exactos de una superficie esférica pueden no tener un cruce común.
- Las direcciones iniciales de los rayos principal y marginal en modo exacto se toman de la solución paraxial: no se resuelve un ajuste exacto para acertar el centro o el borde del stop. Fuera del régimen paraxial, esos nombres designan referencias de construcción.
- Sistema centrado, meridional, superficies esféricas o planas, lentes separadas en aire. No hay superficies asféricas, elementos inclinados, lentes cementadas ni cálculo tridimensional de haces oblicuos.
- La matriz sigue el itinerario axial hasta el primer espejo y su retorno. Una trayectoria exacta con reflexiones internas totales adicionales no tiene necesariamente ese itinerario: sus resultados cardinales no describen esa rama.
- Las líneas físicas son continuas; las prolongaciones virtuales, discontinuas. El plano y la representación de O′ son discontinuos por la convención gráfica solicitada, incluso si la imagen es real; ello no significa que la luz real viaje en líneas discontinuas.
- La mejora de la sagita no elimina toda pérdida de precisión en intersecciones esfera–rayo para radios extremos. Las tolerancias absolutas de geometría están expresadas en mm; no se ha certificado el comportamiento para escalas arbitrarias.
