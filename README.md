# 🗺️ BizLens

> **Filter & Discover Businesses on an Interactive Map**

**Repository**: [https://github.com/al21170365-hub/BizLens](#)  
**Author**: Jose Eduardo Lazcano Beltran  
**Status**: 🟡 Draft  
**Last Updated**: 2025-10-14  

---

## 🎯 Project Overview

BizLens is a web application that enables users to filter and visualize businesses on an interactive map, providing personalized recommendations based on selected business types.

## 🚀 Goals

- Create a page where users can filter one business by type and view one recommendations on a map
- Implement a recommendation system that suggests relevant businesses based on selected filters
- (Stretch Goal) Add additional filters and expand recommendation variety if time permits

## ⚠️ Non-Goals

-  Will not include all existing businesses
- Initial recommendations will focus on less saturated areas for select one business types

## 📋 Background

Inspired by classroom discussions and collaborations with fellow students.

## How to use
### Requierments
- python 3.11

### Install, run flask and steamlit
```bash
git clone https://github.com/al21170365-hub/BizLens.git
cd BizLens
python3.11 -m venv venv
source venv/bin/activate
pip install -r code/requerimientos.txt
cd code
flask run
```
### Open another terminal window
```bash
cd path/to/your/proyect/BizLens
source venv/bin/activate
streamlit run map.py
```
