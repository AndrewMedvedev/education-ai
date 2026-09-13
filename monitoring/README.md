## Alerting rules

### Критические ошибки в сервисе `backend`

```logql
sum(count_over_time({container_name="backend"} |= "ERROR" |~ "(?i)(exception|failed|panic)" [5m]))
```

 - **Condition:** `>3` (больше 3 ошибок за 5 минут)
 - **For:** 2m (чтобы избежать шума в алертах)
 - Severity: Critical

 ### Высокий eror rate для 5xx ошибок

 ```logql
 sum(rate({container_name="backend"} |~ "status=5\\d{2}" [5m])) > 0.05
 ```

 ### Паники / Fatal

 ```
 count_over_time({container_name="backend"} |= "FATAL" [10m]) > 0
 ```

 ### Нет логов от сервиса (heartbeat)

 ```logql
 absent_over_time({container_name="backend"} [10m])
 ```

