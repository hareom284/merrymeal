-- =============================================================
-- MerryMeal — Corrected database schema (MySQL 8 / InnoDB)
-- Covers: meal planning & preparation, food safety,
--         ingredient expiry, prep/cook times, Mon–Fri + frozen-weekend service.
-- drawSQL can import this via "Import > SQL".
-- =============================================================

SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------------------------
---------------
-- People & organisations
-- -------------------------------------------------------------
CREATE TABLE partners (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    legal_name  VARCHAR(255) NOT NULL,
    type        ENUM('charity','restaurant','supplier','corporate') NOT NULL,
    created_at  TIMESTAMP NULL,
    updated_at  TIMESTAMP NULL,
    PRIMARY KEY (id)
);

CREATE TABLE cities (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name        VARCHAR(120) NOT NULL,                 -- was bigint
    created_at  TIMESTAMP NULL,
    updated_at  TIMESTAMP NULL,
    deleted_at  TIMESTAMP NULL,
    PRIMARY KEY (id)
);

CREATE TABLE users (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    full_name   VARCHAR(255) NOT NULL,
    email       VARCHAR(255) NOT NULL,
    password    VARCHAR(255) NOT NULL,                 -- was bigint (store a hash)
    is_active   BOOLEAN NOT NULL DEFAULT 1,            -- renamed from "status"
    role        ENUM('member','volunteer','caregiver','donor','kitchen_staff','admin') NOT NULL,
    dob         DATE NULL,
    partner_id  BIGINT UNSIGNED NULL,                  -- NOT unique: many users per partner
    created_at  TIMESTAMP NULL,                        -- was date
    updated_at  TIMESTAMP NULL,                        -- was date
    deleted_at  TIMESTAMP NULL,                        -- was bigint (soft delete)
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_email (email),
    KEY idx_users_partner (partner_id),
    CONSTRAINT fk_users_partner FOREIGN KEY (partner_id) REFERENCES partners (id)
);

CREATE TABLE user_addresses (                          -- a user may have several addresses
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id     BIGINT UNSIGNED NOT NULL,
    label       VARCHAR(120) NULL,                     -- renamed from "name"
    postal_code VARCHAR(20) NULL,
    city_id     BIGINT UNSIGNED NOT NULL,
    latitude    DECIMAL(10,7) NULL,                    -- needed for the 10 km rule
    longitude   DECIMAL(10,7) NULL,
    created_at  TIMESTAMP NULL,
    updated_at  TIMESTAMP NULL,
    PRIMARY KEY (id),
    KEY idx_addr_user (user_id),
    KEY idx_addr_city (city_id),
    CONSTRAINT fk_addr_user FOREIGN KEY (user_id) REFERENCES users (id),
    CONSTRAINT fk_addr_city FOREIGN KEY (city_id) REFERENCES cities (id)
);

CREATE TABLE member_caregivers (                       -- members linked to caregivers
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    member_id     BIGINT UNSIGNED NOT NULL,
    caregiver_id  BIGINT UNSIGNED NOT NULL,
    relationship  ENUM('family','friend','nurse','social_worker','other') NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_member_caregiver (member_id, caregiver_id),
    CONSTRAINT fk_mc_member    FOREIGN KEY (member_id)    REFERENCES users (id),
    CONSTRAINT fk_mc_caregiver FOREIGN KEY (caregiver_id) REFERENCES users (id)
);

CREATE TABLE volunteer_availabilities (                -- fixed spelling; one volunteer -> many slots
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    volunteer_id  BIGINT UNSIGNED NOT NULL,
    day_of_week   ENUM('mon','tue','wed','thu','fri','sat','sun') NOT NULL,
    day_phrase    ENUM('morning','afternoon','evening') NOT NULL,
    PRIMARY KEY (id),
    KEY idx_avail_volunteer (volunteer_id),
    CONSTRAINT fk_avail_volunteer FOREIGN KEY (volunteer_id) REFERENCES users (id)
);

-- -------------------------------------------------------------
-- Dietary profile (many-to-many)
-- -------------------------------------------------------------
CREATE TABLE diet_preferences (                        -- fixed spelling
    id    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name  VARCHAR(80) NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE diet_preference_user (
    user_id            BIGINT UNSIGNED NOT NULL,
    diet_preference_id BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (user_id, diet_preference_id),          -- composite PK was missing
    CONSTRAINT fk_dpu_user FOREIGN KEY (user_id)            REFERENCES users (id),
    CONSTRAINT fk_dpu_pref FOREIGN KEY (diet_preference_id) REFERENCES diet_preferences (id)
);

CREATE TABLE allergies (                               -- fixed spelling
    id    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name  VARCHAR(80) NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE allergy_user (
    user_id     BIGINT UNSIGNED NOT NULL,
    allergy_id  BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (user_id, allergy_id),                  -- composite PK + the missing user FK
    CONSTRAINT fk_au_user    FOREIGN KEY (user_id)    REFERENCES users (id),
    CONSTRAINT fk_au_allergy FOREIGN KEY (allergy_id) REFERENCES allergies (id)
);

-- -------------------------------------------------------------
-- Kitchens, dishes, ingredients, FOOD SAFETY  (the reassessment)
-- -------------------------------------------------------------
CREATE TABLE kitchens (                                -- NEW: outsourced kitchens (10 km reference point)
    id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name             VARCHAR(160) NOT NULL,
    partner_id       BIGINT UNSIGNED NULL,             -- outsourced kitchen run by a partner
    is_outsourced    BOOLEAN NOT NULL DEFAULT 0,
    latitude         DECIMAL(10,7) NOT NULL,
    longitude        DECIMAL(10,7) NOT NULL,
    service_radius_km DECIMAL(5,2) NOT NULL DEFAULT 10.00,  -- members beyond this get frozen meals
    created_at       TIMESTAMP NULL,
    updated_at       TIMESTAMP NULL,
    PRIMARY KEY (id),
    KEY idx_kitchen_partner (partner_id),
    CONSTRAINT fk_kitchen_partner FOREIGN KEY (partner_id) REFERENCES partners (id)
);

CREATE TABLE meals (                                   -- a dish / recipe
    id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name             VARCHAR(160) NOT NULL,            -- was bigint
    description      TEXT NULL,
    prep_time_minutes  INT UNSIGNED NULL,              -- NEW: preparation time
    cook_time_minutes  INT UNSIGNED NULL,              -- NEW: cooking time
    is_active        BOOLEAN NOT NULL DEFAULT 1,
    created_at       TIMESTAMP NULL,
    updated_at       TIMESTAMP NULL,
    deleted_at       TIMESTAMP NULL,
    PRIMARY KEY (id)
);
-- NOTE: meals.quantity and meals.expired_at were removed.
-- A recipe doesn't expire; physical ingredient stock does (see ingredient_batches),
-- and the amount cooked belongs to a meal_plan, not the recipe.

CREATE TABLE ingredients (                             -- NEW
    id     BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name   VARCHAR(160) NOT NULL,
    unit   ENUM('g','kg','ml','l','unit') NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE meal_ingredients (                        -- NEW: recipe lines (meal <-> ingredient)
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    meal_id       BIGINT UNSIGNED NOT NULL,
    ingredient_id BIGINT UNSIGNED NOT NULL,
    quantity      DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_meal_ingredient (meal_id, ingredient_id),
    CONSTRAINT fk_mi_meal       FOREIGN KEY (meal_id)       REFERENCES meals (id),
    CONSTRAINT fk_mi_ingredient FOREIGN KEY (ingredient_id) REFERENCES ingredients (id)
);

CREATE TABLE ingredient_batches (                      -- NEW: tracks expiration dates of stock
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    ingredient_id   BIGINT UNSIGNED NOT NULL,
    kitchen_id      BIGINT UNSIGNED NOT NULL,
    lot_number      VARCHAR(80) NULL,
    quantity        DECIMAL(10,2) NOT NULL,
    received_at     DATE NULL,
    expiration_date DATE NOT NULL,                      -- THE expiry requirement
    created_at      TIMESTAMP NULL,
    PRIMARY KEY (id),
    KEY idx_batch_ingredient (ingredient_id),
    KEY idx_batch_kitchen (kitchen_id),
    KEY idx_batch_expiry (expiration_date),
    CONSTRAINT fk_batch_ingredient FOREIGN KEY (ingredient_id) REFERENCES ingredients (id),
    CONSTRAINT fk_batch_kitchen    FOREIGN KEY (kitchen_id)    REFERENCES kitchens (id)
);

CREATE TABLE food_safety_checks (                      -- NEW: record of food-safety practices
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    kitchen_id    BIGINT UNSIGNED NOT NULL,
    meal_plan_id  BIGINT UNSIGNED NULL,                -- which batch/menu was checked (optional)
    check_type    ENUM('storage_temp','cooking_temp','cold_chain','hygiene','cleaning','pest_control') NOT NULL,
    temperature_celsius DECIMAL(5,2) NULL,
    result        ENUM('pass','fail') NOT NULL,
    checked_by    BIGINT UNSIGNED NOT NULL,            -- staff user
    checked_at    DATETIME NOT NULL,
    notes         TEXT NULL,
    PRIMARY KEY (id),
    KEY idx_fsc_kitchen (kitchen_id),
    KEY idx_fsc_plan (meal_plan_id),
    CONSTRAINT fk_fsc_kitchen FOREIGN KEY (kitchen_id) REFERENCES kitchens (id),
    CONSTRAINT fk_fsc_checker FOREIGN KEY (checked_by) REFERENCES users (id)
);

-- -------------------------------------------------------------
-- Meal planning  (Mon–Fri fresh; frozen for weekend / >10 km members)
-- -------------------------------------------------------------
CREATE TABLE meal_plans (
    id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    meal_id          BIGINT UNSIGNED NOT NULL,
    kitchen_id       BIGINT UNSIGNED NOT NULL,         -- which kitchen prepares it
    service_date     DATE NOT NULL,
    day_of_week      ENUM('mon','tue','wed','thu','fri','sat','sun') NOT NULL,
    meal_type        ENUM('fresh','frozen') NOT NULL DEFAULT 'fresh',  -- frozen = weekend/out-of-radius
    planned_quantity INT UNSIGNED NOT NULL DEFAULT 0,
    published_by     BIGINT UNSIGNED NOT NULL,
    created_at       TIMESTAMP NULL,                   -- was bigint
    PRIMARY KEY (id),
    KEY idx_plan_meal (meal_id),
    KEY idx_plan_kitchen (kitchen_id),
    CONSTRAINT fk_plan_meal      FOREIGN KEY (meal_id)      REFERENCES meals (id),
    CONSTRAINT fk_plan_kitchen   FOREIGN KEY (kitchen_id)   REFERENCES kitchens (id),
    CONSTRAINT fk_plan_publisher FOREIGN KEY (published_by) REFERENCES users (id)
);

-- link food-safety checks to a specific planned batch (added now that meal_plans exists)
ALTER TABLE food_safety_checks
    ADD CONSTRAINT fk_fsc_plan FOREIGN KEY (meal_plan_id) REFERENCES meal_plans (id);

-- -------------------------------------------------------------
-- Delivery
-- -------------------------------------------------------------
CREATE TABLE routes (
    id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    volunteer_id BIGINT UNSIGNED NOT NULL,
    route_date   DATE NOT NULL,
    status       ENUM('planned','in_progress','completed','cancelled') NOT NULL DEFAULT 'planned',
    created_at   TIMESTAMP NULL,
    updated_at   TIMESTAMP NULL,
    PRIMARY KEY (id),
    KEY idx_route_volunteer (volunteer_id),
    CONSTRAINT fk_route_volunteer FOREIGN KEY (volunteer_id) REFERENCES users (id)
);

CREATE TABLE deliveries (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    route_id        BIGINT UNSIGNED NULL,              -- deliveries now belong to a route
    meal_plan_id    BIGINT UNSIGNED NOT NULL,          -- was "meaL_id" (typo)
    volunteer_id    BIGINT UNSIGNED NOT NULL,
    member_id       BIGINT UNSIGNED NOT NULL,
    member_address_id BIGINT UNSIGNED NOT NULL,        -- where it goes
    meal_type       ENUM('fresh','frozen') NOT NULL DEFAULT 'fresh',
    status          ENUM('pending','out_for_delivery','delivered','failed') NOT NULL DEFAULT 'pending',
    scheduled_date  DATE NULL,
    delivered_time  DATETIME NULL,                     -- was bigint
    latitude        DECIMAL(10,7) NULL,                -- replaced the single "long_lat" text field
    longitude       DECIMAL(10,7) NULL,
    photo           VARCHAR(512) NULL,                 -- proof-of-delivery URL
    created_at      TIMESTAMP NULL,                    -- was bigint
    updated_at      TIMESTAMP NULL,                    -- was bigint
    PRIMARY KEY (id),
    KEY idx_del_route (route_id),
    KEY idx_del_plan (meal_plan_id),
    KEY idx_del_member (member_id),
    CONSTRAINT fk_del_route     FOREIGN KEY (route_id)          REFERENCES routes (id),
    CONSTRAINT fk_del_plan      FOREIGN KEY (meal_plan_id)      REFERENCES meal_plans (id),
    CONSTRAINT fk_del_volunteer FOREIGN KEY (volunteer_id)      REFERENCES users (id),
    CONSTRAINT fk_del_member    FOREIGN KEY (member_id)         REFERENCES users (id),
    CONSTRAINT fk_del_address   FOREIGN KEY (member_address_id) REFERENCES user_addresses (id)
);

CREATE TABLE delivery_feedback (
    id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    delivery_id  BIGINT UNSIGNED NOT NULL,
    rating       TINYINT UNSIGNED NULL,                -- was text; 1–5
    note         LONGTEXT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_feedback_delivery (delivery_id),     -- one feedback per delivery (true 1:1)
    CONSTRAINT fk_feedback_delivery FOREIGN KEY (delivery_id) REFERENCES deliveries (id)
);

-- -------------------------------------------------------------
-- Fundraising
-- -------------------------------------------------------------
CREATE TABLE campaigns (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name        VARCHAR(255) NOT NULL,
    goal_cents  BIGINT UNSIGNED NOT NULL,
    start_at    DATETIME NULL,                         -- was bigint
    end_at      DATETIME NULL,
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    partner_id  BIGINT UNSIGNED NULL,                  -- one partner -> many campaigns
    created_at  TIMESTAMP NULL,
    PRIMARY KEY (id),
    KEY idx_campaign_partner (partner_id),
    CONSTRAINT fk_campaign_partner FOREIGN KEY (partner_id) REFERENCES partners (id)
);

CREATE TABLE donations (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    donor_id        BIGINT UNSIGNED NOT NULL,          -- was "doner_id"
    campaign_id     BIGINT UNSIGNED NOT NULL,          -- was "compaign_id"
    amount_cents    BIGINT UNSIGNED NOT NULL,          -- was text; store integer cents
    payment_type    ENUM('card','bank_transfer','cash','paypal') NOT NULL,  -- was bigint
    status          ENUM('pending','completed','failed','refunded') NOT NULL DEFAULT 'pending', -- was bigint
    transaction_id  VARCHAR(191) NULL,                 -- was bigint; processor refs are strings
    created_at      TIMESTAMP NULL,
    PRIMARY KEY (id),
    KEY idx_don_donor (donor_id),
    KEY idx_don_campaign (campaign_id),
    CONSTRAINT fk_don_donor    FOREIGN KEY (donor_id)    REFERENCES users (id),
    CONSTRAINT fk_don_campaign FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
);

SET FOREIGN_KEY_CHECKS = 1;
