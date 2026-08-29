# Nutrient DWS — Schema Definition (Complete Reference)

Source: https://www.nutrient.io/guides/dws-data-extraction/extract/define-a-schema/

---

## Root Requirements

Root schema MUST be `type: "object"`. Other root types rejected with 400.

## Supported Keywords

| Keyword | Applies to | Description |
|---------|-----------|-------------|
| `type` | all | object, array, string, number, integer, boolean |
| `properties` | objects | Maps property name to nested schema |
| `required` | objects | Fields extraction must always include |
| `items` | arrays | Schema for each array element |
| `description` | all | Field-level guidance for extraction model |
| `enum` | strings | Accepted string values |
| `format: "date"` | strings | Marks field as a date |

## NOT Supported (will be rejected)

- `$ref`, `$defs`
- Composition: `allOf`, `anyOf`, `oneOf`
- Validation: `minimum`, `maxLength`, etc.
- String formats other than `date`
- Conditional: `if`, `then`, `else`
- `additionalProperties` (don't send it)

## Closed Schemas

API returns ONLY declared properties. Treats every schema as `additionalProperties: false`.

## Field Types

### Primitives
```json
{
  "type": "object",
  "properties": {
    "status": { "type": "string", "enum": ["paid", "unpaid", "overdue"], "description": "Payment status" },
    "issue_date": { "type": "string", "format": "date", "description": "Date issued" },
    "is_tax_exempt": { "type": "boolean" }
  }
}
```

### Arrays
```json
{
  "line_items": {
    "type": "array",
    "items": {
      "type": "object",
      "properties": {
        "description": { "type": "string" },
        "quantity": { "type": "integer" },
        "unit_price": { "type": "number" }
      },
      "required": ["description", "quantity", "unit_price"]
    }
  }
}
```

### Nested Objects (up to 5 levels)
```json
{
  "vendor": {
    "type": "object",
    "properties": {
      "name": { "type": "string" },
      "address": {
        "type": "object",
        "properties": {
          "city": { "type": "string" },
          "country": { "type": "string" }
        }
      }
    }
  }
}
```

## Size Limits

| Limit | Value |
|-------|-------|
| Serialized schema size | 32 KB |
| Total fields | 500 |
| Properties per object | 50 |
| Nesting depth | 5 levels |
| Enum values per field | 50 |
| Enum value length | 256 chars |
| Property name length | 128 chars |
| Description length | 1,024 chars |

## Writing Effective Descriptions

- Name the field as it appears in document ("the 'Bill To' company name")
- State expected format ("ISO 4217 currency code", "two-letter country code")
- Disambiguate ("the final total after discounts and tax")
- Use top-level `instructions` for cross-field rules
