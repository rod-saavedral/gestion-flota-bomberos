# Modelo de datos relacional del proyecto Bomberos

Evidencia de sistema: aplicación de base de datos. Fecha de elaboración: 18 de octubre de 2026.

## 1. Objetivo y alcance

Este documento explica cómo se organiza y conecta la información del sistema de gestión de flota y mantenciones de Bomberos implementado sobre Odoo 18 y PostgreSQL. Incluye exclusivamente los módulos bomberos_base, bomberos_fleet y bomberos_maintenance, más sus referencias directas a usuarios, monedas y archivos adjuntos de Odoo.

La evidencia se obtuvo mediante lectura de los modelos Python, las restricciones y los archivos XML de seguridad y configuración del repositorio. No se inició Odoo, no se consultó una base de datos en ejecución y no se utilizaron datos personales ni registros reales. Por tanto, se documenta el esquema esperado al instalar o actualizar estos módulos; no se certifica que una base desplegada esté sincronizada con el código.

## 2. Resumen de la estructura

| Módulo | Tablas propias | Responsabilidad |
| --- | --- | --- |
| bomberos_base | bomberos_company | Compañías de Bomberos, moneda y asignación de usuarios. |
| bomberos_fleet | bomberos_vehicle; bomberos_vehicle_odometer | Unidades, estado operativo, documentos y kilometraje. |
| bomberos_maintenance | bomberos_maintenance_order; bomberos_maintenance_material; bomberos_maintenance_labor; bomberos_maintenance_alert | Órdenes, costos, materiales, trabajo y avisos. |

Existen siete tablas de negocio y dos tablas puente explícitas: bomberos_company_user_rel y bomberos_vehicle_attachment_rel. Las tres tablas estándar representadas como referencia son res_users, res_currency e ir_attachment. Sus demás campos y relaciones internas quedan fuera del esquema para no incluir todo Odoo.

La cadena de dependencias de módulos es: bomberos_maintenance depende de bomberos_fleet; bomberos_fleet depende de bomberos_base; bomberos_base depende de base y web. No hay dependencia declarada de los módulos estándar fleet, maintenance, stock o account. Los vehículos y mantenciones del proyecto son modelos propios, no extensiones de fleet.vehicle ni maintenance.request.

## 3. Cómo interpretar el esquema

El archivo Esquema_relacional_Bomberos.png presenta una vista resumida de las conexiones. Esquema_relacional_Bomberos.mmd contiene el diagrama entidad-relación editable con todas las claves foráneas de negocio representadas, incluidas las compañías derivadas. La imagen simplifica estos enlaces secundarios para mantener su legibilidad.

PK significa clave primaria: identifica una fila. FK significa clave foránea: referencia la clave primaria de otra tabla. UK significa unicidad. Una relación 1:N permite varias filas hijas para una fila padre. Una relación N:M se implementa mediante una tabla puente. En Mermaid, || indica exactamente uno, |o indica cero o uno y o{ indica cero o muchos. Las líneas discontinuas destacan las referencias de compañía derivadas y almacenadas; no significan que carezcan de FK.

Odoo transforma normalmente un nombre de modelo con puntos en un nombre de tabla con guiones bajos: bomberos.maintenance.order corresponde a bomberos_maintenance_order. Los modelos revisados no declaran un nombre de tabla alternativo. El modelo res.users se amplía mediante _inherit: se reutiliza res_users y no se crea otra tabla de usuarios. De igual manera, la ampliación de bomberos.company en bomberos_fleet no crea una segunda tabla de compañías.

Una compañía de Bomberos (bomberos_company) no es una empresa multiempresa estándar de Odoo (res_company). En estos módulos, company_id apunta a bomberos.company. La empresa estándar solo interviene como alternativa para elegir la moneda inicial si no se encuentra CLP; no es una FK de negocio adicional en bomberos_company.

## 4. Relaciones y cardinalidades

| Tabla padre | Tabla hija / campo FK | Cardinalidad | Significado |
| --- | --- | --- | --- |
| res_currency | bomberos_company.currency_id | 1:N | Cada compañía debe tener una moneda; una moneda puede usarse en varias compañías. |
| bomberos_company | bomberos_vehicle.company_id | 1:N | Cada unidad pertenece a una compañía; una compañía puede no tener unidades. |
| bomberos_vehicle | bomberos_vehicle_odometer.vehicle_id | 1:N | Cada lectura pertenece a una unidad; una unidad puede tener muchas lecturas. |
| bomberos_vehicle | bomberos_maintenance_order.vehicle_id | 1:N | Cada orden corresponde a una unidad; la unidad conserva su historial de órdenes. |
| bomberos_maintenance_order | bomberos_maintenance_material.order_id | 1:N | Una orden puede contener cero o más materiales y repuestos. |
| bomberos_maintenance_order | bomberos_maintenance_labor.order_id | 1:N | Una orden puede contener cero o más trabajos de mano de obra. |
| bomberos_maintenance_order | bomberos_maintenance_alert.maintenance_id | 1:N | Cada aviso corresponde a una orden. La unicidad por tipo limita a tres tipos por orden. |
| res_users | odometer.user_id; order.created_by; order.reviewer_id; alert.acknowledged_by | 1:N, opcional en la hija | Identifican quién registra, crea, cierra o revisa; estos cuatro campos no declaran required=True. |
| bomberos_company y res_users | bomberos_company_user_rel | N:M | Un usuario puede estar asignado a varias compañías y cada compañía a varios usuarios. |
| bomberos_vehicle e ir_attachment | bomberos_vehicle_attachment_rel | N:M | Un vehículo puede tener varios archivos y un mismo adjunto puede vincularse a varias unidades. |
| bomberos_company | company_id en lecturas, órdenes, materiales, mano de obra y avisos | 1:N, derivada | Columnas almacenadas que se obtienen por la ruta de relaciones correspondiente. No son asignaciones independientes. |

Las compañías derivadas se obtienen así: lectura y orden desde vehicle_id.company_id; material y mano de obra desde order_id.company_id; aviso desde maintenance_id.company_id. Aunque normalmente tienen valor por la cadena obligatoria, sus declaraciones no establecen explícitamente required=True. Las columnas facilitan búsquedas y reglas de acceso; el ORM debe mantenerlas consistentes.

## 5. Diccionario de datos de negocio

Los tipos siguientes son los esperados según el ORM de esta versión de Odoo: Char y Selection se almacenan como varchar; Text como text; Many2one como integer; Boolean como boolean; Date como date; Datetime como timestamp sin zona horaria, con valores gestionados en UTC por Odoo. Monetary y los Float con digits explícito se almacenan como numeric. Un Float sin digits se almacena como double precision. Selection no crea una tabla catálogo ni un tipo ENUM de PostgreSQL.

En las tablas de negocio, Odoo añade id como PK y, por defecto, create_uid, create_date, write_uid y write_date para auditoría técnica. create_uid y write_uid apuntan a res_users. Se omiten estos enlaces repetidos del diagrama. Las tablas puente tienen PK compuesta por sus dos columnas FK; no tienen el id ni la auditoría de un modelo normal.

### 5.1. bomberos_company

| Campos | Tipo / almacenamiento | Función y condiciones |
| --- | --- | --- |
| name; code | varchar | Ambos obligatorios e indexados; code es único en toda la tabla. |
| active | boolean | Archivado lógico; verdadero por defecto. |
| currency_id | integer, FK a res_currency | Obligatorio. Moneda CLP por defecto si existe; en otro caso, moneda de la empresa activa de Odoo. |
| user_ids | Many2many, sin columna propia | Lado compañía de bomberos_company_user_rel. Solo lectura desde este campo. |
| vehicle_count | Integer calculado, no almacenado | Cuenta vehículos mediante búsqueda; no crea una columna ni una relación adicional. |

### 5.2. bomberos_vehicle

| Campos | Tipo / almacenamiento | Función y condiciones |
| --- | --- | --- |
| name; code; license_plate | varchar | Nombre, código interno y patente; obligatorios e indexados. |
| company_id | integer, FK a bomberos_company | Obligatorio, indexado y con eliminación restrictiva del padre. |
| vehicle_type | varchar, Selection | Obligatorio; pump, rescue, ambulance, tanker, command u other. Por defecto pump. |
| make; model_name; vin; engine_number; capacity | varchar | Marca, modelo, chasis, motor y capacidad o especificación. |
| year | integer | Año; CHECK: nulo o igual o mayor que 1900. |
| operational_state | varchar, Selection | Obligatorio e indexado: available, in_maintenance o unavailable. Por defecto available. |
| current_odometer_km | numeric, Float con digits=(12,1) | Kilometraje actual almacenado; solo lectura en la interfaz; actualizado por la lógica de lecturas. |
| active | boolean | Archivado lógico. |
| odometer_ids | One2many, sin columna propia | Inversa de bomberos_vehicle_odometer.vehicle_id; no utiliza tabla puente. |
| document_ids | Many2many, sin columna propia | Documentos mediante bomberos_vehicle_attachment_rel. |

### 5.3. bomberos_vehicle_odometer

| Campos | Tipo / almacenamiento | Función y condiciones |
| --- | --- | --- |
| vehicle_id | integer, FK a bomberos_vehicle | Obligatorio, indexado; eliminación en cascada desde la unidad. |
| company_id | integer, FK derivada almacenada | Se obtiene de vehicle_id.company_id; indexado. |
| date | date | Obligatorio; fecha actual por defecto según contexto. |
| km | numeric, Float con digits=(12,1) | Obligatorio; CHECK de valor no negativo. |
| user_id | integer, FK a res_users | Usuario registrador; usuario actual por defecto; no obligatorio. |
| note | varchar | Observación libre. |

### 5.4. bomberos_maintenance_order

| Campos | Tipo / almacenamiento | Función y condiciones |
| --- | --- | --- |
| name | varchar | Obligatorio, solo lectura y no copiable; número generado por ir.sequence. No se declara UNIQUE SQL para este campo. |
| maintenance_type | varchar, Selection | Obligatorio e indexado: preventive o reactive. Por defecto preventive. |
| vehicle_id | integer, FK a bomberos_vehicle | Obligatorio e indexado; impide eliminar una unidad con órdenes. |
| company_id | integer, FK derivada almacenada | Se obtiene de vehicle_id.company_id; indexado y de solo lectura. |
| currency_id | Many2one relacionado, no almacenado | Se consulta desde company_id.currency_id; no es columna ni FK propia de esta tabla. |
| state | varchar, Selection | Obligatorio e indexado: draft, scheduled, in_progress, review, done o cancelled. |
| scheduled_date | date | Obligatorio e indexado; fecha actual por defecto. |
| due_odometer_km; odometer_km | numeric, Float con digits=(12,1) | Kilometraje objetivo y al finalizar; cada uno con CHECK de valor nulo o no negativo. |
| started_at; completed_at; reviewed_at | timestamp | Inicio, envío a revisión y cierre real. Solo lectura y no copiables. completed_at no representa el cierre aprobado. |
| created_by; reviewer_id | integer, FK a res_users | Creador y usuario que cierra. created_by tiene usuario actual por defecto; ambos no obligatorios. |
| failure_description; diagnosis; work_description | text | Falla, diagnóstico y trabajo realizado. |
| material_cost; labor_cost; total_cost | numeric, Monetary calculado y almacenado | Totales de materiales y trabajo; total_cost es indexado. |
| material_line_ids; labor_line_ids | One2many, sin columna propia | Inversas de order_id en cada tabla de detalle. |
| active | boolean | Archivado lógico. |

### 5.5. bomberos_maintenance_material

| Campos | Tipo / almacenamiento | Función y condiciones |
| --- | --- | --- |
| order_id | integer, FK a bomberos_maintenance_order | Obligatorio e indexado; eliminación en cascada desde la orden. |
| company_id | integer, FK derivada almacenada | Se obtiene de order_id.company_id; indexado. |
| description | varchar | Material o repuesto; obligatorio. No hay FK a product_product ni integración de inventario declarada. |
| quantity | numeric, Float con digits=(12,2) | Obligatoria, por defecto 1; CHECK mayor que cero. |
| unit | varchar | Unidad de medida en texto; por defecto unidad. |
| unit_cost | numeric, Monetary | Obligatorio, por defecto 0; CHECK no negativo. |
| currency_id | Many2one relacionado, no almacenado | Se consulta desde order_id.currency_id; no crea columna. |
| subtotal | numeric, calculado y almacenado | quantity multiplicada por unit_cost. |

### 5.6. bomberos_maintenance_labor

| Campos | Tipo / almacenamiento | Función y condiciones |
| --- | --- | --- |
| order_id | integer, FK a bomberos_maintenance_order | Obligatorio e indexado; eliminación en cascada desde la orden. |
| company_id | integer, FK derivada almacenada | Se obtiene de order_id.company_id; indexado. |
| description | varchar | Trabajo o especialidad; obligatorio. No hay relación declarada con empleados. |
| hours | numeric, Float con digits=(12,2) | Obligatorias, por defecto 1; CHECK mayor que cero. |
| hourly_rate | numeric, Monetary | Obligatoria, por defecto 0; CHECK no negativo. |
| currency_id | Many2one relacionado, no almacenado | Se consulta desde order_id.currency_id; no crea columna. |
| subtotal | numeric, calculado y almacenado | hours multiplicadas por hourly_rate. |

### 5.7. bomberos_maintenance_alert

| Campos | Tipo / almacenamiento | Función y condiciones |
| --- | --- | --- |
| name; message | varchar | Nombre y detalle del aviso; obligatorios. |
| maintenance_id | integer, FK a bomberos_maintenance_order | Obligatorio e indexado; eliminación en cascada desde la orden. |
| company_id | integer, FK derivada almacenada | Se obtiene de maintenance_id.company_id; indexado. |
| alert_type | varchar, Selection | Obligatorio e indexado: upcoming, overdue o pending_review. |
| active; acknowledged | boolean | Ambos indexados; aviso activo y marca de revisión. |
| acknowledged_by | integer, FK a res_users | Usuario que revisa el aviso; no obligatorio y solo lectura. |
| acknowledged_at | timestamp | Fecha y hora de revisión; solo lectura. |

### 5.8. Tablas puente y referencias estándar

| Tabla o campo | Columnas / destino | Observación |
| --- | --- | --- |
| bomberos_company_user_rel | company_id a bomberos_company.id; user_id a res_users.id | PK compuesta (company_id, user_id); evita repetir la asignación. |
| bomberos_vehicle_attachment_rel | vehicle_id a bomberos_vehicle.id; attachment_id a ir_attachment.id | PK compuesta (vehicle_id, attachment_id); evita repetir el vínculo documental. |
| res_users.bomberos_company_ids | Many2many por bomberos_company_user_rel | Campo añadido al usuario existente; no es columna de res_users. |
| res_users | id y login como referencia resumida | Usuarios de Odoo; sus datos internos y autenticación no se reproducen en el esquema. |
| res_currency | id y name como referencia resumida | Catálogo estándar de monedas. |
| ir_attachment | id y name como referencia resumida | Metadatos y gestión de archivos; el binario puede residir en filestore, no necesariamente dentro de la tabla. |

## 6. Integridad referencial y reglas de negocio

### 6.1. Restricciones aplicadas por PostgreSQL

| Tabla | Restricción declarada |
| --- | --- |
| bomberos_company | UNIQUE(code). |
| bomberos_vehicle | UNIQUE(company_id, code); UNIQUE(company_id, license_plate); CHECK(year IS NULL OR year >= 1900). |
| bomberos_vehicle_odometer | CHECK(km >= 0). |
| bomberos_maintenance_order | CHECK(due_odometer_km IS NULL OR due_odometer_km >= 0); CHECK(odometer_km IS NULL OR odometer_km >= 0). |
| bomberos_maintenance_material | CHECK(quantity > 0); CHECK(unit_cost >= 0). |
| bomberos_maintenance_labor | CHECK(hours > 0); CHECK(hourly_rate >= 0). |
| bomberos_maintenance_alert | UNIQUE(maintenance_id, alert_type). |

El código y la patente de un vehículo son únicos dentro de su compañía, no globalmente. Las claves foráneas y los campos almacenados obligatorios también forman parte del esquema generado por el ORM. Los índices declarados en los modelos aceleran búsquedas por compañía, vehículo, estado, fecha y tipo; por sí solos no definen una relación ni una regla de acceso.

### 6.2. Qué sucede al eliminar registros

La FK bomberos_vehicle.company_id usa restrict: no se puede eliminar una compañía con vehículos. La FK bomberos_maintenance_order.vehicle_id también usa restrict: una unidad con órdenes no se puede eliminar. La FK currency_id de compañía es obligatoria y, según el valor por defecto de Many2one en este Odoo, su eliminación es restrictiva.

La eliminación de una unidad elimina sus lecturas por cascade. La eliminación de una orden elimina sus materiales, mano de obra y avisos por cascade. En las tablas puente, la eliminación de cualquiera de sus extremos elimina el vínculo, no el registro del otro extremo: retirar un vehículo no significa eliminar el archivo compartido ni eliminar un usuario al borrar una asignación.

Los campos de usuario de negocio son opcionales y, al no declarar ondelete, su política ORM es set null. Para los company_id relacionados se documenta su origen, pero no se presupone una política explícita que los módulos no declaran: debe verificarse en el catálogo desplegado si se requiere un inventario físico exacto.

Archivar mediante active=False no equivale a DELETE: el registro y sus relaciones permanecen almacenados. Además de las FK, la posibilidad de borrar está limitada por permisos y por los bloqueos de negocio de cada modelo.

### 6.3. Reglas que dependen del código de Odoo

El código valida que el kilometraje no sea negativo y que una lectura no disminuya respecto del mayor kilometraje registrado o del kilometraje actual. También actualiza el kilometraje de la unidad al crear o editar lecturas. Esta regla de monotonía no es un CHECK SQL entre filas.

Una orden reactiva exige descripción de falla. El código verifica que no exista otra orden en ejecución para el mismo vehículo; esta comprobación no es una restricción UNIQUE SQL y no debe describirse como garantía frente a operaciones concurrentes. Los cambios de estado deben hacerse mediante las acciones del flujo. Para enviar a revisión se exige describir el trabajo realizado. Solo jefatura puede cerrar o cancelar con las condiciones previstas.

Los materiales y la mano de obra no pueden agregarse, modificarse, trasladarse ni eliminarse mediante el ORM cuando la orden está en revisión, cerrada o cancelada. Los costos se calculan así: subtotal de material = quantity por unit_cost; subtotal de trabajo = hours por hourly_rate; total de orden = suma de materiales más suma de mano de obra.

Las validaciones Python, los campos relacionados, los cálculos almacenados y la seguridad se aplican a través del ORM. Escribir directamente con SQL puede omitir estas reglas y dejar datos incoherentes, aunque algunas FK y restricciones SQL sigan vigentes.

## 7. Ejemplo de recorrido de la información

Una compañía tiene un vehículo y asigna usuarios mediante la tabla puente. Al registrar kilometraje, una fila de bomberos_vehicle_odometer apunta a la unidad y al usuario registrador. La compañía de la lectura se deriva del vehículo.

Se crea una orden para esa unidad. La secuencia configurada en ir.sequence utiliza el código bomberos.maintenance.order y un formato como MT-2026-00001. No existe un sequence_id en la orden: el número se solicita por código y se guarda en name. Esta es una dependencia de configuración, no una FK directa de la tabla de órdenes.

La orden sigue draft (borrador), scheduled (programada), in_progress (en ejecución), review (en revisión) y done (cerrada). Puede pasar a cancelled (cancelada) solo desde borrador o programada. Al iniciar cambia el estado operativo de la unidad a in_maintenance. Al enviarla a revisión, si odometer_km tiene un valor distinto de cero, se crea una lectura con el número de orden en note. No existe un maintenance_order_id en la lectura; la relación estructural entre ambas es a través del vehículo, no una FK directa entre lectura y orden.

Los materiales y trabajos apuntan a la orden; sus subtotales alimentan los costos almacenados. El cierre registra reviewer_id y reviewed_at y restaura la disponibilidad de la unidad si no quedan órdenes en ejecución. La fecha completed_at corresponde al envío a revisión, mientras reviewed_at corresponde al cierre.

El archivo cron.xml configura una tarea diaria en ir.cron que invoca _cron_refresh_alerts sobre el modelo de avisos. Considera órdenes programadas o en revisión: genera avisos de vencimiento cuando la fecha es igual o anterior al día actual o se alcanza el kilometraje objetivo; de proximidad dentro de 30 días o a 500 km del objetivo; y de revisión pendiente para órdenes en review. Reutiliza avisos existentes, archiva los que ya no corresponden y reinicia la marca de revisión cuando reactiva un aviso archivado. No hay un cron_id en cada aviso ni una relación directa con un vehículo: se llega al vehículo a través de maintenance_id.vehicle_id.

## 8. Acceso por compañía y perfiles

Los grupos del proyecto son Bombero consultor, Técnico de mantención, Jefe de flota y Administrador de Bomberos. La jerarquía de grupos hace que cada nivel superior implique el anterior. Estos son registros del mecanismo estándar de seguridad de Odoo, no tablas nuevas del dominio Bomberos.

Los archivos security/rules.xml filtran compañías por las asignaciones de user.bomberos_company_ids. En vehículos, lecturas, órdenes, materiales, mano de obra y avisos utilizan company_id para limitar el acceso a las compañías asignadas; las reglas de jefatura permiten acceso a todos los registros de estos modelos. Los archivos ir.model.access.csv determinan los permisos de operación por modelo. Los administradores heredan el grupo de jefatura.

La asignación de compañías y el perfil son conceptos diferentes: la tabla bomberos_company_user_rel determina el ámbito de compañías; los grupos y permisos estándar determinan qué operaciones se pueden hacer. No son políticas de seguridad por fila de PostgreSQL, y una conexión SQL directa no aplica automáticamente estas reglas del ORM.

## 9. Consultas de lectura ilustrativas

Estas consultas muestran las uniones entre tablas y no fueron ejecutadas contra una base instalada. Solo deben usarse con acceso autorizado; las consultas SQL directas no aplican las reglas de acceso del usuario de Odoo. No se incluyen sentencias de modificación.

```sql
SELECT c.name AS compania, v.code AS unidad,
       v.license_plate AS patente, o.name AS orden,
       o.state AS estado, o.total_cost AS costo_total,
       cur.name AS moneda
FROM bomberos_maintenance_order AS o
JOIN bomberos_vehicle AS v ON v.id = o.vehicle_id
JOIN bomberos_company AS c ON c.id = v.company_id
JOIN res_currency AS cur ON cur.id = c.currency_id
ORDER BY c.name, v.code, o.scheduled_date DESC;
```

```sql
SELECT u.login AS usuario, c.code AS codigo_compania,
       c.name AS compania
FROM bomberos_company_user_rel AS rel
JOIN res_users AS u ON u.id = rel.user_id
JOIN bomberos_company AS c ON c.id = rel.company_id
ORDER BY u.login, c.code;
```

No conviene unir simultáneamente todas las líneas de materiales y de mano de obra para luego sumar: una orden con dos materiales y tres trabajos produciría seis combinaciones y podría duplicar los importes. Para informes, se pueden usar los totales almacenados de la orden o agregar cada detalle por separado antes de unirlo.

## 10. Fuentes, archivos y verificación

Las rutas siguientes son relativas a la raíz del repositorio y permiten contrastar la evidencia con su implementación.

| Fuente | Información contrastada |
| --- | --- |
| Software/custom-addons/bomberos_base/models/company.py | Compañía, moneda, tabla puente y código único. |
| Software/custom-addons/bomberos_base/models/res_users.py | Ampliación del usuario y asignación de compañías. |
| Software/custom-addons/bomberos_fleet/models/company.py | Contador de vehículos no almacenado. |
| Software/custom-addons/bomberos_fleet/models/vehicle.py | Unidad, documentos, estado y restricciones. |
| Software/custom-addons/bomberos_fleet/models/vehicle_odometer.py | Lecturas, compañía derivada y actualización de kilometraje. |
| Software/custom-addons/bomberos_maintenance/models/maintenance.py | Orden, materiales, mano de obra, costos y flujo. |
| Software/custom-addons/bomberos_maintenance/models/maintenance_alert.py | Avisos, unicidad, revisión y actualización automática. |
| __manifest__.py de los tres módulos | Dependencias y archivos cargados. |
| security/groups.xml, security/rules.xml e ir.model.access.csv | Perfiles, ámbito por compañía y permisos. |
| bomberos_maintenance/data/sequence.xml y data/cron.xml | Numeración de órdenes y tarea diaria. |
| Software/odoo-18.0/odoo/fields.py | Tipos SQL, FK Many2one y PK compuestas de tablas Many2many. |

Se verificó estáticamente que los siete modelos y las dos tablas puente del esquema existen en las fuentes. Las referencias de los diagramas y los campos documentados se contrastaron con los modelos. No se comprobaron el catálogo PostgreSQL desplegado, el estado de instalación de los módulos ni la ejecución de las consultas de ejemplo.

El informe se entrega en Markdown editable, Word y PDF. Se adjuntan el esquema en PNG y su fuente Mermaid. El script generar_evidencia.py permite volver a producir el Word, el PDF y la imagen a partir del informe y de las fuentes locales sin iniciar Odoo. Requiere python-docx, Pillow y reportlab; el entorno Software/.venv312 dispone de ellos en la fecha de elaboración.