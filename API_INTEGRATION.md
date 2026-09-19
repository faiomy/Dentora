# Dentora — API & Integration (`/api/v1`)

طبقة REST + Webhooks تسمح لأنظمة خارجية (n8n, نوتيفيكيشن, تطبيقات ويب…)
بالقراءة والكتابة عن بعد، مع نظام مفاتيح API بصلاحيات متدرجة.

> **الأصل**: كل البيانات في قاعدة SQLite المحلية (`database.py` هي مصدر الحقيقة الوحيد).
> الـ API مجرد واجهة فوقها — مش نسخة منفصلة.

---

## 1) التشغيل

- من الإعدادات → «الوصول للـ API» شغّل الخادم وحدد العنوان والمنفذ.
- مباشرة بعد التسجيل، أنشئ مفتاح API واختار صلاحياته. **المفتاح الكامل يظهر
  مرة واحدة فقط** ولا يمكن استرجاعه لاحقًا (مخزّن كـ SHA-256 hash).
- الوصول بالافتراضي على `http://127.0.0.1:8100` مدعوم بالتوثيق `Authorization: Bearer <key>`.

تشغيل منفصل عن الواجهة (للتطوير/الاختبار):

```
python -m api                     # يقرأ نفس إعدادات قاعدة البيانات
```

### الوصول من الشبكة (LAN)

الافتراضي `host=127.0.0.1` يعني **هذا الجهاز فقط** — لأي جهاز آخر على الشبكة
يجب تعيين `host=0.0.0.0` صراحة في إعدادات الوصول للـ API، وتفتيح المنفذ من
الجدار الناري (الأمان مسؤوليتك — النطاقات لا تغني عن HTTPS/شبكة خاصة).

---

## 2) المصادقة والصلاحيات

كل طلب (عدا `/health`) يتطلب header:

```
Authorization: Bearer dentora_xxxxxxxx...
```

Codes الاستجابة:
| كود HTTP | `error.code` | المعنى |
|---|---|---|
| 401 | `missing_api_key` | لا يوجد header |
| 401 | `invalid_api_key` | مفتاح غير صحيح |
| 403 | `api_key_disabled` | المفتاح موقوف من الإعدادات |
| 403 | `insufficient_scope` | المفتاح صالح لكن بدون الصلاحية المطلوبة |
| 404 | …`not_found` | المورد غير موجود |
| 422 | `validation_error` | بيانات الطلب غير صحيحة (مع تفاصيل الحقول) |

### النطاقات (Scopes)

| عملية | النطاق المطلوب |
|---|---|
| GET لموارد | `{resource}.read` |
| POST/PATCH | `{resource}.write` |
| DELETE | `{resource}.delete` |

قاعدة صارمة: كل صلاحية **منفصلة** — `write` لا تشمل `read` أو `delete`،
و`read` لا تشمل أي كتابة. النطاقات المتوفرة:

```
patients.read     patients.write     patients.delete
appointments.read appointments.write appointments.delete
visits.read       visits.write       visits.delete
financials.read   financials.write   financials.delete
odontogram.read   odontogram.write   events.read
```

---

## 3) الموارد والمسارات

الاستجابة دائمًا مؤطرة:

```json
{ "data": { ... } | [ ... ] | null, "meta": { "page": 1, "page_size": 50, "total": 12, "pages": 1 } }
```

الخطأ:

```json
{ "error": { "code": "validation_error", "message": "...", "details": { "errors": [...] } } }
```

### المرضى `patients`
| الطريقة | المسار | الوصف |
|---|---|---|
| GET | `/api/v1/patients?page=&page_size=&search=` | قائمة (search بالاسم/الهاتف) |
| POST | `/api/v1/patients` | إنشاء |
| GET | `/api/v1/patients/{id}` | مريض واحد |
| PATCH | `/api/v1/patients/{id}` | تعديل (حقول جزئية) |
| GET | `/api/v1/patients/{id}/profile` | ملف كامل مع زيارات ومعاملات |

### المواعيد `appointments`
| الطريقة | المسار |
|---|---|
| GET | `/api/v1/appointments?appt_date=YYYY-MM-DD&status=` |
| POST | `/api/v1/appointments` |
| GET | `/api/v1/appointments/{id}` |
| PATCH | `/api/v1/appointments/{id}` |
| POST | `/api/v1/appointments/{id}/cancel` |

### الزيارات `visits` (تابعة لمريض)
| الطريقة | المسار |
|---|---|
| GET | `/api/v1/patients/{pid}/visits` |
| POST | `/api/v1/patients/{pid}/visits` |
| GET | `/api/v1/visits/{id}` |
| PATCH | `/api/v1/visits/{id}` |
| DELETE | `/api/v1/visits/{id}` |

### الحسابات `financials` (تابعة لمريض)
| الطريقة | المسار |
|---|---|
| GET | `/api/v1/patients/{pid}/financials` |
| GET | `/api/v1/patients/{pid}/balance` |
| POST | `/api/v1/patients/{pid}/transactions` (`tx_type`: charge \| payment \| discount) |
| GET | `/api/v1/transactions/{id}` |
| PATCH | `/api/v1/transactions/{id}` |
| DELETE | `/api/v1/transactions/{id}` |

### خريطة الأسنان `odontogram`
| الطريقة | المسار |
|---|---|
| GET | `/api/v1/patients/{pid}/odontogram` |
| PATCH | `/api/v1/patients/{pid}/odontogram/tooth/{tooth}` (`status`, `notes`) |
| PUT/DELETE | `/api/v1/patients/{pid}/odontogram/annotation/{tooth}` |
| POST | `/api/v1/patients/{pid}/odontogram/treatments` (يسجل معالجة + charge تلقائيًا) |

### النظام
| الطريقة | المسار |
|---|---|
| GET | `/api/v1/health` (بدون مصادقة) |
| GET | `/api/v1/events?limit=` (سجل الأحداث، يتطلب `events.read`) |

توثيق تفاعلي: `GET /docs` (Swagger UI) — اكتب المفتاح هناك لتجربة مباشرة.

---

## 4) الأحداث والـ Webhooks

كل عملية كتابة تنشئ حدثًا موثقًا في `event_log`، وإذا هناك webhooks مشتركين
بيتم توصيله له في الخلفية:

| الحدث | متى |
|---|---|
| `patient.created` / `patient.updated` | إنشاء/تعديل مريض |
| `appointment.created` / `appointment.updated` / `appointment.cancelled` | المواعيد |
| `visit.created` / `visit.updated` | الزيارات |
| `payment.created` | فقط عند تسجيل حركة `payment` (دفعة) |
| `test.ping` | زر «إرسال تجربة» من الإعدادات |

جسم الحدث المرسل:

```json
{
  "event_id": "uuid",
  "event_type": "patient.created",
  "timestamp": "2026-09-19T16:28:18.792820+03:00",
  "resource": "patient",
  "data": { "id": 7, "full_name": "..." }
}
```

### التوقيع (HMAC)
الطلب المرسل للـ webhook يحمل:

```
X-Dentora-Signature: sha256=<hex(hmac-sha256(secret, raw_body))>
X-Dentora-Event-Id:   <نفس event_id>
X-Dentora-Timestamp:  <ISO>
```

التحقق من جهة المستقبِل (مثال n8n/pseudo):

```
expected = hmac_sha256(secret, request.body).hexdigest()
if !constant_time_equals("sha256=" + expected, header): reject
```

### إعادة المحاولة
- `max_attempts` (افتراضي 3) بفاصل `attempt` ثانية.
- كل محاولة مسجلة في `webhook_deliveries` مع `attempt` / `http_status` / `error`.
- `last_status` على الـ webhook نفسه يعكس آخر توصيل (`delivered` / `failed`).

---

## 5) مثال n8n ← Dentora (HTTP + Bearer)

في عقدة **HTTP Request** من n8n:

```
Method   : POST
URL      : http://<dentora-host>:8100/api/v1/patients
Headers  : Authorization = Bearer dentora_xxx...
Body (JSON):
{
  "full_name": "{{ $json.patientName }}",
  "phone": "{{ $json.phone }}",
  "gender": "male"
}
```

النتيجة `200` تعني إنشاء المريض في النظام فورًا (ونفس اللحظة تتحرك
`patient.created` لأي webhook تاني مشترك).

مثال عكسي Dentora ← n8n: أنشئ **Webhook URL** في n8n (POST)، ومن إعدادات
الوصول للـ API أضف webhook بنفس العنوان ونفس `secret`، واشترك في
`patient.created`. هيوصل الحدث موقّعًا بـ HMAC لتتأكد إنه من Dentora.

---

## 6) حدود معروفة

- **عنوان محلي فقط** ما لم تحدّث الـ host بنفسك (شبكة LAN).
- لا توجد OAuth — مفتاح API واحد بشبكة نطاقات (جرّده لأقل صلاحية لازمة).
- المفاتيح والـ webhooks لا تُدار إلا من إعدادات البرنامج، **ليس** بمسارات REST.
- إدارة مستخدمي الواجهة / كلمات المرور خطها الحارس — لا يشملها الـ API.
- توصيل الـ webhooks في الخلفية (بحد أقصى لحظي) — للضمانية تستخدم
  `webhook_deliveries` في السجل.

## 7) اختبارات

من جذر المشروع:

```
python -m tests.api_tests        # مصادقة/نطاقات/CRUD/أحداث (TestClient)
python -m tests.webhook_tests    # توقيع HMAC/تسليم/مهلة/إعادة محاولة
python -m tests.api_demo         # الاتجاهان عبر HTTP حقيقي + webhook
```

على ويندوز شغّلها مع `PYTHONIOENCODING=utf-8` (أو `$env:PYTHONIOENCODING='utf-8'`
في PowerShell) لو الطرفية بتطبع cp1252.

## 8) قيود معروفة (v1)

- طابور الأحداث في الذاكرة (thread لكل webhook) — لو البرنامج اتقفل وقت
  الإرسال، المحاولة بتضيع. تسليم دائم 100% محتاج `webhook_deliveries` +
  إعادة جدولة عند الإقلاع (تحسين مخطط لـ v2).
- لا توجد مسارات REST لإدارة المفاتيح أو الـ webhooks — إدارتهم من
  إعدادات البرنامج فقط (قرار أمني مقصود).
- نطاق `test.ping` الحدث اليدوي متاح للتحقق السريع من الاتصال.
- توقيع HMAC مشفر بصيغة `sha256=<hex>` في هيدر `X-Dentora-Signature`،
  مع `X-Dentora-Event-Id` و `X-Dentora-Timestamp` للتحقق والتكرار.
- HTTPS غير مُفعّل محليًا — استخدم شبكة موثوقة أو tunnel مشفّر للوصول البعيد.