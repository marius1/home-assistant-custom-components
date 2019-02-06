# Home Assistant custom components
This repo contains [Home Assistant](https://www.home-assistant.io/) custom components.

## HVC sensor
Dynamically adds sensors for the garbage types that are collected for your address. It will contain the next date the garbage type will be picked up. To find the sensors look in states overview in Home Assistant.

To configure add the following in configuration.yaml
```yaml
sensor:
  - platform: hvc
    postalcode: 1507AL
    housenumber: 150
```
