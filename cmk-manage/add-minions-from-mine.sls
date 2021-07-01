{% set site = pillar['cmk-master']['site'] %}
{% set user = pillar['cmk-master']['automation-user'] %}
{% set secret = pillar['cmk-master']['automation-secret'] %}
{% set port = pillar['cmk-master']['port'] %}
{% set graintags = pillar['cmk-master']['graintags'] %}
{% set mine_data = salt['mine.get']('roles:checkmk_agent', 'cmk-agent-ip,manufacturer,osfinger,virtual,productname,datacenter,role,kernel', tgt_type='grain') %}
{% set mine_agent_ips = salt['mine.get']('roles:checkmk_agent', 'cmk-agent-ip', tgt_type='grain') %}


# It is necessary to do this before you add your hosts to the monitoring system,
# because a Host-Tag must exist before you are able to assign them.

ensure-hosttags-present-in-wato:
  cmk-manage.hosttags_present:
    - name : hosttags_present
    - target : localhost
    - cmk_site : {{ site }}
    - cmk_user : {{ user }}
    - cmk_secret : {{ secret }}
    - port : {{ port }}
    - tag_groups:
        {% for graintag in graintags %}
          {{ graintag }}:
            id : {{ graintag }}
            title : {{ graintag }}
            topic : Salt Grains
            tags:
            {% for grain, data in mine_data.items() %}
              {% if graintag == grain %}
              {% for host, tag in data.items() %}
              - id : "{{ graintag }}_{{ tag }}"
                title : "{{ tag }}"
                aux_tags: []
              {% endfor %}
              {% endif %}
            {% endfor %}
        {% endfor %}

{% for host, agent_ip in mine_agent_ips.items() %}
ensure-host-in-wato-{{ host }}:
  cmk-manage.host_present:
    - name : {{ host}}
    - target : localhost
    - cmk_site : {{ site }}
    - cmk_user : {{ user }}
    - cmk_secret : {{ secret }}
    - port : {{ port }}
    - discover: False
    - ipaddress : {{ agent_ip }}
    - alias : {{ host }}
    - folder : Salt/{{ mine_data['kernel'][host] }}
    - tags: {
        {% for graintag in graintags -%}
          {% set last_grain_tag = None %}
          {% for grain, tag in mine_data.items() -%}
            {% if last_grain_tag == grain %}{% continue %}{% endif %}
            {% if graintag == grain -%}
                {{ graintag }}: '{{ graintag }}_{{ tag[host] }}',
            {% endif %}
            {% set last_grain_tag = grain %}
          {% endfor %}
        {% endfor %}
            } 
{% endfor %}