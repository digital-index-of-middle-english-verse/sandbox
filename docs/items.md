---
layout: page
title: Verse items
permalink: /items/
---


<ul>

{% for item in site.items %}

  <li>
  <a href="{{ item.url | relative_url }}">
    {{ item.itemIncipit }} - DIMEV {{ item.DIMEV }}
  </a>
  </li>
{% endfor %}
</ul>
