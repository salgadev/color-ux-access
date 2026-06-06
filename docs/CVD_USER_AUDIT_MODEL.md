# CVD User-Centric Audit Model
# Entendiendo la auditoría desde la perspectiva del usuario daltónico

## El problema central

El usuario daltónico no ve "colores incorrectos" — ve **ambigüedad funcional**. Cuando un diseño depende del color para transmitir estado, acción o significado, el usuario daltónico enfrentaincertidumbre en tiempo real.

**Ejemplo real:**
- Campo de formulario con borde rojo (error) vs borde verde (válido) → para deutéranopes ambos se ven idéntico (ambos marrones-grisáceos)
- El usuario no sabe si su formulario fue aceptado o si hay errores hasta que lee el texto de ayuda o depende de otro indicador

## Lo que el usuario daltónico realmente hace en una página

Flujo mental típico:

1. **Ve una interfaz** → solicita acción (ej: "submit")
2. **Evalúa los elementos visibles** → busca botones, campos, indicadores
3. **Los elementos que dependen de color no transmiten su estado** → requiere inferencia adicional o prueba-y-error
4. **Si no hay etiqueta textual, icono dedicado, o contraste de brillo, el elemento es inaccesible**

### Elementos típicamente fallidos

| Elemento | Cómo falla para CVD | Qué depende el usuario |
|----------|---------------------|------------------------|
| Form validation borders | Error (rojo) vs success (verde) se confunden | Texto de error, icono con etiqueta, o contraste de brillo |
| Nav active state | Color activo vs inactivo idéntico | Forma, borde, texto, posición |
| Botones primario/secundario | Verde vs rojo indistinguibles | Etiqueta textual, icono, brillo |
| Status badges | Online (verde) vs offline (rojo) se confunden | Icono + texto, no solo color |
| Gráficos/datos | Series codificadas por color indistinguibles | Patrones, etiquetas de datos |
| Links | Solo azul vs texto negro, ambos oscuros | Subrayado, hover state |
| Required field markers | Asterisco rojo no visible | Texto "required", borde diferente |

## El modelo de auditoría propuesto

### Concepto: "Confusión como señal de inaccesibilidad"

```
Screenshot → Simular CVD → Pedir al modelo que describa elementos específicos
                                              ↓
                          Si el modelo se confunde = el diseño es inaccesible
                          para usuarios daltónicos reales
```

**Analogía:** El modelo de visión funciona como un "usuario proxy" bajo la simulación CVD. Cuando el modelo no puede distinguir un botón de otro, el usuario daltónico tampoco puede.

### Implementación ligera (lighter model)

En lugar de analizar toda la imagen con un VLM grande:
1. **Cortar/recortar** la región de interés (un formulario, un conjunto de botones, una tabla de datos)
2. **Prompt específico:** "Describe este formulario: ¿qué campos son requeridos? ¿qué botón es 'submit' vs 'cancel'? ¿hay indicadores de error?"
3. **El modelo responde con lo que infiere** — si infiere incorrectamente, eso es un hallazgo

### Ejemplo de prompt por región

```
You are viewing this page as a person with deuteranopia (red-green color blindness).
Describe the form below. Specifically:
- Which button is the primary action (submit/continue)?
- Which button is the secondary/cancel action?
- Are there any visible error states on the fields?
- Is there a "required" indicator on any field?
- Can you tell which fields have validation errors vs success?
```

### Respuesta → Hallazgo CVD

| Respuesta del modelo | Hallazgo |
|---------------------|----------|
| "Both buttons look the same to me" | Los botones no son distinguibles sin color |
| "I can't tell which field has an error" | Estados de validación invisibles |
| "No required markers visible" | Indicadores de requeridos inaccesibles |
| "The submit button appears disabled" | Contraste insuficiente para estado activo |

## Por qué esto funciona mejor que WCAG automatizado

WCAG tradicional verifica ratios de contraste, requisitos de color, y heurísticas. Pero:

1. **WCAG puede pasar** (contraste suficiente) y aún ser **inutilizable** para CVD si la codificación de color es el único diferenciador
2. **Un revisor humano daltónico** podría identificar el problema, pero es lento y costoso
3. **La simulación + VLM** captura la experiencia real del usuario daltónico a escala

## Variantes CVD y sus confusiones específicas

| CVD | Qué confunde | Impacto en UI típico |
|-----|-------------|----------------------|
| Deuteranopia (más común) | Rojo=verde, marrón=verde oscuro | Form validation, status badges, buttons |
| Protanopia | Rojo=negro, verde=marrón | Errores, alertas rojas invisibles |
| Tritanopia | Azul=verde, amarillo=naranja | Gráficos, indicadores de temperatura/color |
| Achromatopsia | Todo en escala de grises | Depende enteramente de brillo/forma |

## Siguiente paso

Documentar este modelo en `vlm/analyzer.py` con:
- `audit_region(screenshot, region_coords, cvd_type)` → descripción + hallazgos
- `interpret_cvd_confusion(description, cvd_type)` → clasificación de problema
- Pool de variantes CVD para cubrir todas las categorías

## Preguntas para Carlos

1. ¿Para el flujo de auditoría — debería ser primero CVD simulation → análisis por región, o primero identificar regiones problemáticas y luego simular CVD solo en esas?
2. ¿El modelo ligero debería describir la región o evaluar si es "accessible" explícitamente?
3. ¿Hay elementos específicos além de forms/buttons que。我们要 prioritizing first?