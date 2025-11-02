# 🧪 Тестирование - Краткая памятка

## 🎯 Два подхода - Выберите нужный

### ⚡ Быстрый (5-8 минут)
```bash
pytest tests/test_comprehensive_performance.py -v -m "not longrun"
```
- Диалоги НЕ показываются
- Для разработки и CI/CD

### 🎭 Реалистичный (10-15 минут)
```bash
pytest tests/test_gui_with_dialogs.py -v -s
```
- Диалоги показываются и автоматически закрываются
- Для финальной проверки

---

## 📋 Что тестируется

✅ Время отклика GUI < 500ms  
✅ Failure rate < 1%  
✅ Линейный рост памяти  
✅ Загрузка < 5 сек/100K строк  
✅ Точность ML > 95%  
✅ Деградация < 15%  

---

## 🔧 Настройка (Windows)

```powershell
# PowerShell
$env:QT_QPA_PLATFORM="offscreen"
pytest tests/test_comprehensive_performance.py -v
```

```cmd
# CMD
set QT_QPA_PLATFORM=offscreen
pytest tests/test_comprehensive_performance.py -v
```

---

## 📚 Документация

- `БЫСТРЫЙ_СТАРТ_НОВЫЕ_ТЕСТЫ.md` - **НАЧНИТЕ ЗДЕСЬ!**
- `ДВА_ПОДХОДА_К_ТЕСТИРОВАНИЮ.md` - Сравнение подходов
- `ФИНАЛЬНАЯ_СВОДКА.md` - Полная информация

---

## 💡 Быстрые команды

### Разработка
```bash
pytest tests/test_comprehensive_performance.py::TestGUIResponseTime -v
```

### Перед коммитом
```bash
pytest tests/test_comprehensive_performance.py -v -m "not longrun"
```

### Перед релизом
```bash
pytest tests/test_gui_with_dialogs.py -v -s -m "not load"
```

---

**Всего: 33 теста покрывают все 6 требований!** ✅

