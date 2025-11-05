-- Database initialization script
-- Generated from kubota_db schema

-- 外部キー制約を一時的に無効化
SET FOREIGN_KEY_CHECKS=0;

USE kubota_db;

-- Table: company_calendar
CREATE TABLE `company_calendar` (
  `id` int NOT NULL AUTO_INCREMENT,
  `calendar_date` date NOT NULL,
  `day_type` enum('営業日','休日','祝日','特別休業') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '営業日',
  `day_name` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '祝日名など',
  `is_working_day` tinyint(1) NOT NULL DEFAULT '1',
  `notes` text COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `calendar_date` (`calendar_date`),
  KEY `idx_date` (`calendar_date`),
  KEY `idx_working` (`is_working_day`)
) ENGINE=InnoDB AUTO_INCREMENT=323 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: container_capacity
CREATE TABLE `container_capacity` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `width` int NOT NULL COMMENT '容器の幅（mm）',
  `depth` int NOT NULL COMMENT '容器の奥行（mm）',
  `height` int NOT NULL COMMENT '容器の高さ（mm）',
  `max_weight` int DEFAULT '0' COMMENT '最大重量（kg）',
  `max_volume` decimal(10,2) GENERATED ALWAYS AS ((((`width` * `depth`) * `height`) / 1000000000.0)) STORED COMMENT '容積（m³換算）',
  `can_mix` tinyint(1) DEFAULT '1' COMMENT '他の容器と混載可能か',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `stackable` tinyint(1) DEFAULT '1' COMMENT '段積み可能か',
  `max_stack` int DEFAULT '1' COMMENT '最大積み重ね段数',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: csv_import_history
CREATE TABLE `csv_import_history` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT 'インポートID',
  `filename` varchar(255) NOT NULL COMMENT 'ファイル名',
  `import_date` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'インポート日時',
  `record_count` int DEFAULT '0' COMMENT '登録件数',
  `status` varchar(20) DEFAULT '成功' COMMENT 'ステータス',
  `message` text COMMENT 'メッセージ',
  PRIMARY KEY (`id`),
  KEY `idx_import_date` (`import_date`)
) ENGINE=InnoDB AUTO_INCREMENT=181 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='CSVインポート履歴';

-- Table: delivery_progress
CREATE TABLE `delivery_progress` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '進度ID',
  `order_id` varchar(50) NOT NULL COMMENT 'オーダーID',
  `product_id` int NOT NULL COMMENT '製品ID',
  `order_date` date NOT NULL COMMENT '受注日',
  `delivery_date` date NOT NULL COMMENT '納期',
  `order_quantity` int NOT NULL COMMENT '受注数量',
  `manual_planning_quantity` int DEFAULT NULL,
  `planned_quantity` int DEFAULT '0' COMMENT '計画積載数量',
  `shipped_quantity` int DEFAULT '0' COMMENT '出荷済み数量',
  `shipped_remaining_quantity` int DEFAULT '0',
  `planned_progress_quantity` int DEFAULT NULL,
  `remaining_quantity` int GENERATED ALWAYS AS ((`order_quantity` - `shipped_quantity`)) STORED COMMENT '残数量',
  `status` varchar(20) DEFAULT '未出荷',
  `customer_code` varchar(20) DEFAULT NULL COMMENT '得意先コード',
  `customer_name` varchar(100) DEFAULT NULL COMMENT '得意先名',
  `order_type` varchar(16) NOT NULL DEFAULT '内示',
  `order_number` varchar(50) DEFAULT NULL,
  `delivery_location` varchar(100) DEFAULT NULL COMMENT '納入先',
  `priority` int DEFAULT '5' COMMENT '優先度（1:最高 〜 10:最低）',
  `notes` text COMMENT '備考',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '作成日時',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新日時',
  PRIMARY KEY (`id`),
  KEY `idx_delivery_date` (`delivery_date`),
  KEY `idx_product_id` (`product_id`),
  KEY `idx_status` (`status`),
  KEY `idx_order_date` (`order_date`),
  CONSTRAINT `fk_delivery_progress_products` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=805 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='納入進度マスタ';

-- Table: loading_plan_detail
CREATE TABLE `loading_plan_detail` (
  `id` int NOT NULL AUTO_INCREMENT,
  `plan_id` int NOT NULL COMMENT '計画ID',
  `loading_date` date NOT NULL COMMENT '積載日',
  `truck_id` int NOT NULL COMMENT 'トラックID',
  `truck_name` varchar(50) DEFAULT NULL COMMENT 'トラック名',
  `trip_number` int DEFAULT '1' COMMENT '便番号',
  `product_id` int NOT NULL COMMENT '製品ID',
  `product_code` varchar(20) DEFAULT NULL COMMENT '製品コード',
  `product_name` varchar(100) DEFAULT NULL COMMENT '製品名',
  `container_id` int NOT NULL COMMENT '容器ID',
  `num_containers` int NOT NULL COMMENT '容器数',
  `total_quantity` int NOT NULL COMMENT '合計数量',
  `delivery_date` date NOT NULL COMMENT '納期',
  `is_advanced` tinyint(1) DEFAULT '0' COMMENT '前倒しフラグ',
  `original_date` date DEFAULT NULL COMMENT '元の積載予定日',
  `volume_utilization` decimal(5,2) DEFAULT NULL COMMENT '体積積載率(%)',
  `weight_utilization` decimal(5,2) DEFAULT NULL COMMENT '重量積載率(%)',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_plan_date` (`plan_id`,`loading_date`),
  KEY `idx_truck` (`truck_id`),
  KEY `idx_product` (`product_id`),
  CONSTRAINT `loading_plan_detail_ibfk_1` FOREIGN KEY (`plan_id`) REFERENCES `loading_plan_header` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=11412 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='積載計画明細';

-- Table: loading_plan_edit_history
CREATE TABLE `loading_plan_edit_history` (
  `id` int NOT NULL AUTO_INCREMENT,
  `plan_id` int NOT NULL,
  `edit_date` datetime DEFAULT CURRENT_TIMESTAMP,
  `user_id` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `field_changed` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `old_value` text COLLATE utf8mb4_unicode_ci,
  `new_value` text COLLATE utf8mb4_unicode_ci,
  `detail_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `plan_id` (`plan_id`),
  KEY `detail_id` (`detail_id`),
  CONSTRAINT `loading_plan_edit_history_ibfk_1` FOREIGN KEY (`plan_id`) REFERENCES `loading_plan_header` (`id`) ON DELETE CASCADE,
  CONSTRAINT `loading_plan_edit_history_ibfk_2` FOREIGN KEY (`detail_id`) REFERENCES `loading_plan_detail` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=103 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: loading_plan_header
CREATE TABLE `loading_plan_header` (
  `id` int NOT NULL AUTO_INCREMENT,
  `plan_name` varchar(100) NOT NULL COMMENT '計画名',
  `start_date` date NOT NULL COMMENT '計画開始日',
  `end_date` date NOT NULL COMMENT '計画終了日',
  `total_days` int NOT NULL COMMENT '計画日数',
  `total_trips` int NOT NULL COMMENT '総便数',
  `status` varchar(20) DEFAULT '作成済' COMMENT 'ステータス',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `created_by` varchar(50) DEFAULT NULL COMMENT '作成者',
  `notes` text COMMENT '備考',
  `exported_at` timestamp NULL DEFAULT NULL COMMENT 'Excel出力日時',
  `exported_by` varchar(50) DEFAULT NULL COMMENT '出力者',
  `is_confirmed` tinyint(1) DEFAULT '0' COMMENT '計画確定フラグ',
  `confirmed_at` timestamp NULL DEFAULT NULL COMMENT '確定日時',
  PRIMARY KEY (`id`),
  KEY `idx_start_date` (`start_date`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB AUTO_INCREMENT=162 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='積載計画ヘッダー';

-- Table: loading_plan_unloaded
CREATE TABLE `loading_plan_unloaded` (
  `id` int NOT NULL AUTO_INCREMENT,
  `plan_id` int NOT NULL COMMENT '計画ID',
  `product_id` int NOT NULL COMMENT '製品ID',
  `product_code` varchar(20) DEFAULT NULL COMMENT '製品コード',
  `product_name` varchar(100) DEFAULT NULL COMMENT '製品名',
  `container_id` int DEFAULT NULL COMMENT '容器ID',
  `num_containers` int DEFAULT NULL COMMENT '必要容器数',
  `total_quantity` int DEFAULT NULL COMMENT '合計数量',
  `delivery_date` date DEFAULT NULL COMMENT '納期',
  `reason` text COMMENT '積載不可理由',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_plan` (`plan_id`),
  CONSTRAINT `loading_plan_unloaded_ibfk_1` FOREIGN KEY (`plan_id`) REFERENCES `loading_plan_header` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=239 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='積載不可アイテム';

-- Table: loading_plan_versions
CREATE TABLE `loading_plan_versions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `plan_id` int NOT NULL,
  `version_number` int NOT NULL,
  `version_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `created_by` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `snapshot_data` json DEFAULT NULL,
  `notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_plan_version` (`plan_id`,`version_number`),
  CONSTRAINT `loading_plan_versions_ibfk_1` FOREIGN KEY (`plan_id`) REFERENCES `loading_plan_header` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: loading_plan_warnings
CREATE TABLE `loading_plan_warnings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `plan_id` int NOT NULL COMMENT '計画ID',
  `warning_date` date NOT NULL COMMENT '警告日付',
  `warning_type` varchar(20) DEFAULT NULL COMMENT '警告タイプ',
  `warning_message` text COMMENT '警告メッセージ',
  `product_id` int DEFAULT NULL COMMENT '関連製品ID',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_plan` (`plan_id`),
  CONSTRAINT `loading_plan_warnings_ibfk_1` FOREIGN KEY (`plan_id`) REFERENCES `loading_plan_header` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=810 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='積載計画警告';

-- Table: monthly_summary
CREATE TABLE `monthly_summary` (
  `id` int NOT NULL AUTO_INCREMENT,
  `product_id` int DEFAULT NULL,
  `month_type` enum('first','next','next_next') DEFAULT NULL,
  `total_quantity` int DEFAULT NULL,
  `month_year` varchar(6) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_month_summary` (`product_id`,`month_type`,`month_year`),
  CONSTRAINT `fk_monthly_summary_products` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4729 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: page_permissions
CREATE TABLE `page_permissions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `role_id` int NOT NULL,
  `page_name` varchar(255) NOT NULL,
  `can_view` tinyint(1) DEFAULT '1',
  `can_edit` tinyint(1) DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_role_page` (`role_id`,`page_name`),
  KEY `idx_role_id` (`role_id`),
  CONSTRAINT `page_permissions_ibfk_1` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=153 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: product_container_mapping
CREATE TABLE `product_container_mapping` (
  `id` int NOT NULL AUTO_INCREMENT,
  `product_id` int NOT NULL,
  `container_id` int NOT NULL,
  `max_quantity` int DEFAULT '100' COMMENT '容器あたりの最大積載数',
  `is_primary` tinyint(1) DEFAULT '0' COMMENT '主要容器フラグ',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_product_container` (`product_id`,`container_id`),
  KEY `container_id` (`container_id`),
  CONSTRAINT `fk_product_container_products` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE,
  CONSTRAINT `product_container_mapping_ibfk_2` FOREIGN KEY (`container_id`) REFERENCES `container_capacity` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='製品と容器の紐付けマスタ';

-- Table: product_groups
CREATE TABLE `product_groups` (
  `id` int NOT NULL AUTO_INCREMENT,
  `group_code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '製品群コード（英数字）',
  `group_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '製品群名（日本語）',
  `description` text COLLATE utf8mb4_unicode_ci COMMENT '説明',
  `enable_container_management` tinyint(1) DEFAULT '1' COMMENT '容器管理有効',
  `enable_transport_planning` tinyint(1) DEFAULT '1' COMMENT '輸送計画有効',
  `enable_progress_tracking` tinyint(1) DEFAULT '1' COMMENT '進捗管理有効',
  `enable_inventory_management` tinyint(1) DEFAULT '0' COMMENT '在庫管理有効',
  `default_lead_time_days` int DEFAULT '2' COMMENT 'デフォルトリードタイム（日）',
  `default_priority` int DEFAULT '5' COMMENT 'デフォルト優先度（1-10）',
  `is_active` tinyint(1) DEFAULT '1' COMMENT '有効/無効',
  `display_order` int DEFAULT '0' COMMENT '表示順序',
  `notes` text COLLATE utf8mb4_unicode_ci COMMENT '備考',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '作成日時',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新日時',
  PRIMARY KEY (`id`),
  UNIQUE KEY `group_code` (`group_code`),
  UNIQUE KEY `group_name` (`group_name`),
  KEY `idx_group_code` (`group_code`),
  KEY `idx_is_active` (`is_active`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='製品群マスタ';

-- Table: production_constraints
CREATE TABLE `production_constraints` (
  `id` int NOT NULL AUTO_INCREMENT,
  `product_id` int NOT NULL,
  `daily_capacity` int NOT NULL DEFAULT '1000',
  `smoothing_level` decimal(5,2) NOT NULL DEFAULT '0.70',
  `volume_per_unit` decimal(10,2) NOT NULL DEFAULT '1.00',
  `is_transport_constrained` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_product_constraint` (`product_id`),
  CONSTRAINT `fk_production_constraints_products` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=57 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: production_instructions_detail
CREATE TABLE `production_instructions_detail` (
  `id` int NOT NULL AUTO_INCREMENT,
  `product_id` int DEFAULT NULL,
  `record_type` varchar(10) DEFAULT NULL,
  `order_type` varchar(16) NOT NULL DEFAULT '内示',
  `order_number` varchar(50) DEFAULT NULL,
  `start_month` varchar(10) DEFAULT NULL,
  `total_first_month` int DEFAULT NULL,
  `total_next_month` int DEFAULT NULL,
  `total_next_next_month` int DEFAULT NULL,
  `instruction_date` date DEFAULT NULL,
  `instruction_quantity` int DEFAULT NULL,
  `inspection_category` varchar(10) DEFAULT NULL,
  `month_type` enum('first','next','next_next') DEFAULT NULL,
  `day_number` int DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_instruction` (`product_id`,`instruction_date`,`inspection_category`),
  KEY `idx_date_product` (`instruction_date`,`product_id`),
  KEY `idx_month_type` (`month_type`),
  CONSTRAINT `fk_production_instructions_products` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3688 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: production_plan
CREATE TABLE `production_plan` (
  `id` int NOT NULL AUTO_INCREMENT,
  `product_id` int NOT NULL,
  `planned_date` date NOT NULL COMMENT '計画日',
  `planned_quantity` int NOT NULL COMMENT '計画数量',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_production_plan_products` (`product_id`),
  CONSTRAINT `fk_production_plan_products` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: products
CREATE TABLE `products` (
  `id` int NOT NULL AUTO_INCREMENT,
  `product_code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `product_name` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `model_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '機種名',
  `product_group_id` int DEFAULT NULL COMMENT '製品群ID',
  `display_id` int NOT NULL DEFAULT '0',
  `delivery_location` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `box_type` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `capacity` int DEFAULT '1',
  `container_width` int DEFAULT NULL,
  `container_depth` int DEFAULT NULL,
  `container_height` int DEFAULT NULL,
  `stackable` tinyint(1) DEFAULT '1',
  `can_advance` tinyint(1) DEFAULT '0' COMMENT '前倒し可能フラグ(平準化対象)',
  `lead_time_days` int NOT NULL DEFAULT '0' COMMENT 'リードタイム日数（納品日の何日前に積載するか）',
  `fixed_point_days` int NOT NULL DEFAULT '0' COMMENT '固定日数',
  `used_container_id` int DEFAULT NULL COMMENT 'この製品が使用する容器',
  `used_truck_ids` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '使用トラックID（カンマ区切り）',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `inspection_category` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `product_code` (`product_code`),
  KEY `fk_products_containe_new` (`used_container_id`),
  KEY `idx_product_group_id` (`product_group_id`),
  CONSTRAINT `fk_products_containe_new` FOREIGN KEY (`used_container_id`) REFERENCES `container_capacity` (`id`),
  CONSTRAINT `fk_products_product_group` FOREIGN KEY (`product_group_id`) REFERENCES `product_groups` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: products_syosai
CREATE TABLE `products_syosai` (
  `id` int NOT NULL AUTO_INCREMENT,
  `data_no` int DEFAULT NULL,
  `factory` varchar(10) DEFAULT NULL,
  `client_code` int DEFAULT NULL,
  `calculation_date` date DEFAULT NULL,
  `production_complete_date` date DEFAULT NULL,
  `modified_factory` varchar(10) DEFAULT NULL,
  `product_category` varchar(10) DEFAULT NULL,
  `product_code` varchar(20) DEFAULT NULL,
  `ac_code` varchar(10) DEFAULT NULL,
  `processing_content` varchar(100) DEFAULT NULL,
  `product_name` varchar(100) DEFAULT NULL,
  `delivery_location` varchar(50) DEFAULT NULL,
  `box_type` varchar(10) DEFAULT NULL,
  `capacity` int DEFAULT NULL,
  `grouping_category` varchar(10) DEFAULT NULL,
  `form_category` varchar(10) DEFAULT NULL,
  `inspection_category` varchar(10) DEFAULT NULL,
  `ordering_category` varchar(10) DEFAULT NULL,
  `regular_replenishment_category` varchar(10) DEFAULT NULL,
  `lead_time` int DEFAULT NULL,
  `fixed_point_days` int DEFAULT NULL,
  `shipping_factory` varchar(10) DEFAULT NULL,
  `client_product_code` varchar(50) DEFAULT NULL,
  `purchasing_org` varchar(10) DEFAULT NULL,
  `item_group` varchar(10) DEFAULT NULL,
  `processing_type` varchar(10) DEFAULT NULL,
  `inventory_transfer_category` varchar(10) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `container_width` int DEFAULT NULL,
  `container_depth` int DEFAULT NULL,
  `container_height` int DEFAULT NULL,
  `stackable` tinyint(1) DEFAULT '1',
  `can_advance` tinyint(1) DEFAULT '0' COMMENT '前倒し可能フラグ(平準化対象)',
  `used_container_id` int DEFAULT NULL COMMENT 'この製品が使用する容器',
  `used_truck_ids` varchar(100) DEFAULT NULL COMMENT '使用トラックID（カンマ区切り）',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_product` (`data_no`,`product_code`,`inspection_category`),
  KEY `fk_products_container` (`used_container_id`),
  CONSTRAINT `fk_products_container` FOREIGN KEY (`used_container_id`) REFERENCES `container_capacity` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=52 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: roles
CREATE TABLE `roles` (
  `id` int NOT NULL AUTO_INCREMENT,
  `role_name` varchar(255) NOT NULL,
  `description` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `role_name` (`role_name`),
  KEY `idx_role_name` (`role_name`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: shipment_records
CREATE TABLE `shipment_records` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '出荷ID',
  `progress_id` int NOT NULL COMMENT '進度ID',
  `plan_id` int DEFAULT NULL COMMENT '積載計画ID',
  `truck_id` int DEFAULT NULL COMMENT 'トラックID',
  `shipment_date` date NOT NULL COMMENT '出荷日',
  `shipped_quantity` int NOT NULL COMMENT '出荷数量',
  `container_id` int DEFAULT NULL COMMENT '使用容器ID',
  `num_containers` int DEFAULT NULL COMMENT '容器数',
  `actual_departure_time` datetime DEFAULT NULL COMMENT '実出発時刻',
  `actual_arrival_time` datetime DEFAULT NULL COMMENT '実到着時刻',
  `driver_name` varchar(50) DEFAULT NULL COMMENT 'ドライバー名',
  `notes` text COMMENT '備考',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '作成日時',
  PRIMARY KEY (`id`),
  KEY `truck_id` (`truck_id`),
  KEY `container_id` (`container_id`),
  KEY `idx_shipment_date` (`shipment_date`),
  KEY `idx_progress_id` (`progress_id`),
  KEY `idx_plan_id` (`plan_id`),
  CONSTRAINT `shipment_records_ibfk_1` FOREIGN KEY (`progress_id`) REFERENCES `delivery_progress` (`id`) ON DELETE CASCADE,
  CONSTRAINT `shipment_records_ibfk_2` FOREIGN KEY (`plan_id`) REFERENCES `loading_plan_header` (`id`) ON DELETE SET NULL,
  CONSTRAINT `shipment_records_ibfk_3` FOREIGN KEY (`truck_id`) REFERENCES `truck_master` (`id`) ON DELETE SET NULL,
  CONSTRAINT `shipment_records_ibfk_4` FOREIGN KEY (`container_id`) REFERENCES `container_capacity` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=367 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='出荷実績';

-- Table: tab_permissions
CREATE TABLE `tab_permissions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `role_id` int NOT NULL,
  `page_name` varchar(255) NOT NULL,
  `tab_name` varchar(255) NOT NULL,
  `can_view` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `can_edit` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_role_page_tab` (`role_id`,`page_name`,`tab_name`),
  KEY `idx_role_page` (`role_id`,`page_name`),
  CONSTRAINT `tab_permissions_ibfk_1` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=27 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: transport_constraints
CREATE TABLE `transport_constraints` (
  `id` int NOT NULL AUTO_INCREMENT,
  `max_daily_volume` decimal(10,2) NOT NULL DEFAULT '100.00',
  `max_daily_trucks` int NOT NULL DEFAULT '5',
  `truck_capacity` decimal(10,2) NOT NULL DEFAULT '20.00',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: transport_plans
CREATE TABLE `transport_plans` (
  `id` int NOT NULL AUTO_INCREMENT,
  `product_id` int NOT NULL,
  `container_id` int DEFAULT NULL,
  `truck_id` int DEFAULT NULL,
  `quantity` int NOT NULL,
  `scheduled_date` date NOT NULL,
  PRIMARY KEY (`id`),
  KEY `container_id` (`container_id`),
  KEY `truck_id` (`truck_id`),
  KEY `fk_transport_plans_products` (`product_id`),
  CONSTRAINT `fk_transport_plans_products` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE,
  CONSTRAINT `transport_plans_ibfk_2` FOREIGN KEY (`container_id`) REFERENCES `container_capacity` (`id`) ON DELETE SET NULL,
  CONSTRAINT `transport_plans_ibfk_3` FOREIGN KEY (`truck_id`) REFERENCES `truck_master` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: truck_container_rules
CREATE TABLE `truck_container_rules` (
  `id` int NOT NULL AUTO_INCREMENT,
  `truck_id` int NOT NULL COMMENT '紐づくトラックID',
  `container_id` int NOT NULL COMMENT '紐づく容器ID',
  `max_quantity` int DEFAULT NULL COMMENT 'この便に積める最大容器数（NULLなら物理制約のみ）',
  `priority` int DEFAULT '0' COMMENT '積載優先度（小さいほど優先）',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_truck_container` (`truck_id`,`container_id`),
  KEY `container_id` (`container_id`),
  CONSTRAINT `truck_container_rules_ibfk_1` FOREIGN KEY (`truck_id`) REFERENCES `truck_master` (`id`) ON DELETE CASCADE,
  CONSTRAINT `truck_container_rules_ibfk_2` FOREIGN KEY (`container_id`) REFERENCES `container_capacity` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: truck_master
CREATE TABLE `truck_master` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'トラックの名前（例：1便、トラックAなど）',
  `width` int NOT NULL COMMENT '荷台の幅（mm）',
  `depth` int NOT NULL COMMENT '荷台の奥行（mm）',
  `height` int NOT NULL COMMENT '荷台の高さ（mm）',
  `max_weight` int DEFAULT '10000' COMMENT '最大積載重量（kg）',
  `departure_time` time NOT NULL COMMENT '出発時刻',
  `arrival_time` time NOT NULL COMMENT '到着時刻',
  `default_use` tinyint(1) DEFAULT '0' COMMENT 'デフォルトで使用される便かどうか',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '作成日時',
  `arrival_day_offset` int DEFAULT '0' COMMENT '到着日オフセット（日数: 0=当日, 1=翌日, 2=翌々日 …)',
  `priority_product_codes` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table: user_roles
CREATE TABLE `user_roles` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `role_id` int NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_user_role` (`user_id`,`role_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_role_id` (`role_id`),
  CONSTRAINT `user_roles_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `user_roles_ibfk_2` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: users
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(255) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `full_name` varchar(255) NOT NULL,
  `email` varchar(255) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT '1',
  `is_admin` tinyint(1) DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `last_login` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  KEY `idx_username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- View: v_container_managed_products
CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `v_container_managed_products` AS select `p`.`id` AS `id`,`p`.`product_code` AS `product_code`,`p`.`product_name` AS `product_name`,`p`.`product_group_id` AS `product_group_id`,`p`.`display_id` AS `display_id`,`p`.`delivery_location` AS `delivery_location`,`p`.`box_type` AS `box_type`,`p`.`capacity` AS `capacity`,`p`.`container_width` AS `container_width`,`p`.`container_depth` AS `container_depth`,`p`.`container_height` AS `container_height`,`p`.`stackable` AS `stackable`,`p`.`can_advance` AS `can_advance`,`p`.`lead_time_days` AS `lead_time_days`,`p`.`fixed_point_days` AS `fixed_point_days`,`p`.`used_container_id` AS `used_container_id`,`p`.`used_truck_ids` AS `used_truck_ids`,`p`.`created_at` AS `created_at`,`p`.`inspection_category` AS `inspection_category`,`pg`.`group_code` AS `group_code`,`pg`.`group_name` AS `group_name` from (`products` `p` join `product_groups` `pg` on((`p`.`product_group_id` = `pg`.`id`))) where ((`pg`.`enable_container_management` = true) and (`pg`.`is_active` = true));

-- View: v_delivery_progress_summary
CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `v_delivery_progress_summary` AS select `dp`.`id` AS `id`,`dp`.`order_id` AS `order_id`,`dp`.`product_id` AS `product_id`,`p`.`product_code` AS `product_code`,`p`.`product_name` AS `product_name`,`dp`.`order_date` AS `order_date`,`dp`.`delivery_date` AS `delivery_date`,`dp`.`order_quantity` AS `order_quantity`,`dp`.`shipped_quantity` AS `shipped_quantity`,`dp`.`remaining_quantity` AS `remaining_quantity`,`dp`.`status` AS `status`,`dp`.`customer_name` AS `customer_name`,`dp`.`delivery_location` AS `delivery_location`,`dp`.`priority` AS `priority`,(to_days(`dp`.`delivery_date`) - to_days(curdate())) AS `days_to_delivery`,(case when (`dp`.`status` = '出荷完了') then '✅' when ((to_days(`dp`.`delivery_date`) - to_days(curdate())) < 0) then '🔴遅延' when ((to_days(`dp`.`delivery_date`) - to_days(curdate())) <= 3) then '🟡緊急' else '🟢' end) AS `urgency_flag` from (`delivery_progress` `dp` left join `products` `p` on((`dp`.`product_id` = `p`.`id`))) order by `dp`.`delivery_date`,`dp`.`priority`;

-- View: v_delivery_progress_with_next_planned
CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `v_delivery_progress_with_next_planned` AS select `dp`.`id` AS `id`,`dp`.`order_id` AS `order_id`,`dp`.`product_id` AS `product_id`,`dp`.`order_date` AS `order_date`,`dp`.`delivery_date` AS `delivery_date`,`dp`.`order_quantity` AS `order_quantity`,`dp`.`planned_quantity` AS `planned_quantity`,`dp`.`shipped_quantity` AS `shipped_quantity`,`dp`.`remaining_quantity` AS `remaining_quantity`,`dp`.`status` AS `status`,`dp`.`customer_code` AS `customer_code`,`dp`.`customer_name` AS `customer_name`,`dp`.`delivery_location` AS `delivery_location`,`dp`.`priority` AS `priority`,`dp`.`notes` AS `notes`,`dp`.`created_at` AS `created_at`,`dp`.`updated_at` AS `updated_at`,(coalesce((select (sum(`dp2`.`shipped_quantity`) - sum(`dp2`.`order_quantity`)) from `delivery_progress` `dp2` where ((`dp2`.`product_id` = `dp`.`product_id`) and (`dp2`.`delivery_date` < `dp`.`delivery_date`))),0) + (case when (coalesce(`dp`.`shipped_quantity`,0) > 0) then (`dp`.`shipped_quantity` - `dp`.`order_quantity`) else (coalesce(`dp`.`planned_quantity`,0) - `dp`.`order_quantity`) end)) AS `next_planned_quantity` from `delivery_progress` `dp`;

-- View: v_loading_plan_with_progress
CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `v_loading_plan_with_progress` AS select `lpd`.`plan_id` AS `plan_id`,`lph`.`plan_name` AS `plan_name`,`lpd`.`loading_date` AS `loading_date`,`lpd`.`truck_name` AS `truck_name`,`lpd`.`product_code` AS `product_code`,`lpd`.`product_name` AS `product_name`,`lpd`.`num_containers` AS `num_containers`,`lpd`.`total_quantity` AS `total_quantity`,`lpd`.`delivery_date` AS `delivery_date`,`dp`.`order_id` AS `order_id`,`dp`.`customer_name` AS `customer_name`,`dp`.`remaining_quantity` AS `remaining_quantity`,`dp`.`status` AS `progress_status` from ((`loading_plan_detail` `lpd` left join `loading_plan_header` `lph` on((`lpd`.`plan_id` = `lph`.`id`))) left join `delivery_progress` `dp` on(((`lpd`.`product_id` = `dp`.`product_id`) and (`lpd`.`delivery_date` = `dp`.`delivery_date`)))) order by `lpd`.`loading_date`,`lpd`.`truck_id`;

-- View: v_managed_products
CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `v_managed_products` AS select `p`.`id` AS `id`,`p`.`product_code` AS `product_code`,`p`.`product_name` AS `product_name`,`p`.`product_group_id` AS `product_group_id`,`p`.`display_id` AS `display_id`,`p`.`delivery_location` AS `delivery_location`,`p`.`box_type` AS `box_type`,`p`.`capacity` AS `capacity`,`p`.`container_width` AS `container_width`,`p`.`container_depth` AS `container_depth`,`p`.`container_height` AS `container_height`,`p`.`stackable` AS `stackable`,`p`.`can_advance` AS `can_advance`,`p`.`lead_time_days` AS `lead_time_days`,`p`.`fixed_point_days` AS `fixed_point_days`,`p`.`used_container_id` AS `used_container_id`,`p`.`used_truck_ids` AS `used_truck_ids`,`p`.`created_at` AS `created_at`,`p`.`inspection_category` AS `inspection_category`,`pg`.`group_code` AS `group_code`,`pg`.`group_name` AS `group_name`,`pg`.`enable_container_management` AS `enable_container_management`,`pg`.`enable_transport_planning` AS `enable_transport_planning`,`pg`.`enable_progress_tracking` AS `enable_progress_tracking` from (`products` `p` join `product_groups` `pg` on((`p`.`product_group_id` = `pg`.`id`))) where (`pg`.`is_active` = true);

-- Table: カレンダー
CREATE TABLE `カレンダー` (
  `日付` date NOT NULL,
  `曜日` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`日付`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: タンク構成部品表
CREATE TABLE `タンク構成部品表` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `完成品番号` varchar(50) NOT NULL,
  `部番` varchar(50) NOT NULL,
  `使用数` int unsigned DEFAULT '1',
  `加工先` varchar(100) DEFAULT NULL,
  `加工先番号` varchar(50) DEFAULT NULL,
  `LT` int unsigned DEFAULT '0',
  PRIMARY KEY (`ID`),
  KEY `idx_parent` (`完成品番号`),
  KEY `idx_child` (`部番`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Table: タンク計画
CREATE TABLE `タンク計画` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `日付` date NOT NULL,
  `完成品番号` varchar(50) NOT NULL,
  `内示` int unsigned DEFAULT '0',
  `確定` int unsigned DEFAULT '0',
  `計画` int unsigned DEFAULT '0',
  `実績` int unsigned DEFAULT '0',
  `計進` int unsigned DEFAULT '0',
  `進度` int unsigned DEFAULT '0',
  `注番` varchar(50) DEFAULT NULL,
  `受注` int unsigned DEFAULT '0',
  PRIMARY KEY (`ID`),
  UNIQUE KEY `uq_date_part` (`日付`,`完成品番号`),
  KEY `idx_date` (`日付`),
  KEY `idx_part` (`完成品番号`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- 外部キー制約を再有効化
SET FOREIGN_KEY_CHECKS=1;
