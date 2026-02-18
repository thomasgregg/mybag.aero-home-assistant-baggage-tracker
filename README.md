# Mybag.aero Baggage Tracker

Home Assistant custom integration for tracking delayed baggage status from mybag.aero.

Supported airlines:
- Austrian
- Lufthansa
- Swiss

## What you get
For each configured baggage file, the integration creates:
- `sensor.<name>_status`
- `binary_sensor.<name>_found`

`sensor` state values:
- `searching`
- `located`
- `received`
- `scheduled_for_delivery`
- `delivered`
- `not_found`
- `error`

Useful sensor attributes:
- `airline`
- `reference_number`
- `family_name`
- `bag_title`
- `headline`
- `details`
- `tracing_statuses`
- `primary_tracing_status`
- `status_steps`
- `current_status_text`
- `status_body`
- `delivery_details`
- `no_of_bags_updated`
- `record_status`
- `message`
- `checked_at`
- `source_url`
- `raw_excerpt`

## Limitations
- Multi-bag delayed baggage reports (more than one luggage piece in one report) are not tested.
- It may work, but behavior is currently unknown because no suitable sample data was available for testing.

## Install (End User, via HACS)
1. Open Home Assistant.
2. Go to `HACS -> Integrations -> Custom repositories`.
3. Add this repository URL as type `Integration`:
   - `https://github.com/thomasgregg/mybag.aero-home-assistant-baggage-tracker`
4. Install `Mybag.aero Baggage Tracker` from HACS.
5. Restart Home Assistant.
6. Go to `Settings -> Devices & Services -> Add Integration`.
7. Search for `Mybag.aero Baggage Tracker`.
8. Enter:
   - Airline (`austrian`, `lufthansa`, `swiss`)
   - Reference number in file-reference format (for example `ABCOS12345`)
   - Family name
   - Scan interval in minutes

## Dashboard UI Example
You can paste this as a manual Lovelace card (`type: vertical-stack`) and adapt entity IDs to your setup.

![Dashboard overview](docs/images/ha-dashboard-main-2026-02-18.png)
![Delivery details card](docs/images/ha-dashboard-delivery-2026-02-18.png)

```yaml
type: vertical-stack
cards:
  - type: grid
    columns: 2
    square: false
    cards:
      - type: tile
        entity: sensor.mybag_beros22525_status
        name: Baggage Status
        icon: mdi:bag-checked
        state_content:
          - state
          - last_updated
        vertical: false
        features_position: bottom
      - type: tile
        entity: binary_sensor.mybag_beros22525_found
        name: Bag Found
        icon: mdi:bag-checked
        state_content:
          - state
  - type: markdown
    content: >
      {% set e = 'sensor.mybag_beros22525_status' %}

      {% set s = states(e) %}

      {% set bag_title = state_attr(e, 'bag_title') %}

      {% set airline = state_attr(e, 'airline') %}

      {% set ref = state_attr(e, 'reference_number') %}

      {% set checked = state_attr(e, 'checked_at') %}

      {% set current = state_attr(e, 'current_status_text') %}

      {% set body = state_attr(e, 'status_body') %}

      {% set steps = state_attr(e, 'status_steps') %}


      {% set current_norm = (current or '') | lower | replace('.', '') %}

      {% set body_norm = (body or '') | lower | replace('.', '') %}

      {% set show_body = body and (body_norm not in current_norm) and
      (current_norm not in body_norm) %}


      ## {{ bag_title if bag_title else 'Delayed Baggage' }}


      **Airline:** {{ airline|title }}  

      **Reference:** {{ ref }}  

      **Current state:** `{{ s }}`  

      {% if checked %}**Last check:** {{ as_timestamp(checked) |
      timestamp_custom('%Y-%m-%d %H:%M:%S') }}{% endif %}


      {% if current %}


      ### Current status


      {{ current }}


      {% endif %}


      {% if show_body %}


      {{ body }}


      {% endif %}


      {% if steps and steps | length > 0 %}


      ### Progress


      {% for step in steps %}


      - {{ step }}


      {% endfor %}


      {% endif %}
  - type: conditional
    conditions:
      - condition: state
        entity: sensor.mybag_beros22525_status
        state_not: searching
      - condition: state
        entity: sensor.mybag_beros22525_status
        state_not: not_found
      - condition: state
        entity: sensor.mybag_beros22525_status
        state_not: error
    card:
      type: markdown
      content: >-
        {% set d = state_attr('sensor.mybag_beros22525_status',
        'delivery_details') or {} %}

        ## Delivery details

        {% if d.get('created_by') %}**Created by:** {{ d.get('created_by') }}{%
        endif %}

        {% if d.get('number_of_baggage_in_delivery') %}**Number of baggage:** {{
        d.get('number_of_baggage_in_delivery') }}{% endif %}

        {% if d.get('delivery_service') %}**Delivery service:** {{
        d.get('delivery_service') }}{% endif %}

        {% if d.get('pickup_datetime_local') %}**Picked up:** {{
        d.get('pickup_datetime_local') }}{% endif %}

        {% if d.get('scheduled_delivery_local') %}**Scheduled delivery:** {{
        d.get('scheduled_delivery_local') }}{% endif %}

        {% if d.get('delivered_datetime_local') %}**Delivered:** {{
        d.get('delivered_datetime_local') }}{% endif %}

        {% if d.get('commission_date') %}**Date of commission:** {{
        d.get('commission_date') }}{% endif %}

        {% if d.get('courier_website') %}**Courier website:** {{
        d.get('courier_website') }}{% endif %}

        {% if d.get('passenger_name') %}**Passenger name:** {{
        d.get('passenger_name') }}{% endif %}

        {% if d.get('delivery_address') %}**Delivery address:** {{
        d.get('delivery_address') }}{% endif %}

        {% if d.get('telephone_number') %}**Telephone number:** {{
        d.get('telephone_number') }}{% endif %}

        {% if d.get('baggage_type') %}**Baggage type:** {{ d.get('baggage_type')
        }}{% endif %}

        {% if d.get('baggage_colour') %}**Baggage colour:** {{
        d.get('baggage_colour') }}{% endif %}

        {% if d.get('tag_details') %}**Tag details:** {{ d.get('tag_details')
        }}{% endif %}

        {% if d.get('courier_tracking_url') %}**Tracking:** [{{
        d.get('courier_tracking_url') }}]({{ d.get('courier_tracking_url') }}){%
        endif %}


        {% if d.get('note') %}

        **Please note**  
        {% set note_text = d.get('note')
          | replace('\r\n', ' ')
          | replace('\n', ' ')
          | replace('\r', ' ')
          | replace('  ', ' ')
          | replace('  ', ' ')
          | trim %}
        {{ note_text }}

        {% endif %}
```
