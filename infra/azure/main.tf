terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.0"
    }
  }
}

provider "azurerm" {
  features {}
}

variable "location" {
  type    = string
  default = "East US 2"
}
variable "name" {
  type    = string
  default = "quorumflow"
}

variable "storage_name" {
  type        = string
  description = "Globally unique lowercase storage account name."
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${var.name}"
  location = var.location
}

resource "azurerm_storage_account" "lake" {
  name                     = var.storage_name
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "ZRS"
  is_hns_enabled           = true
  min_tls_version          = "TLS1_2"
  tags = {
    system = var.name
    layer  = "hadoop-history"
  }
}

resource "azurerm_storage_container" "artifacts" {
  name                  = "artifacts"
  storage_account_id    = azurerm_storage_account.lake.id
  container_access_type = "private"
}

resource "azurerm_container_registry" "runtime" {
  name                = replace("${var.storage_name}acr", "-", "")
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = false
}

output "artifact_endpoint" {
  value = azurerm_storage_account.lake.primary_dfs_endpoint
}

output "registry" {
  value = azurerm_container_registry.runtime.login_server
}
