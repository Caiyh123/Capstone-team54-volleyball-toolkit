list.of.packages <- c("jsonlite", "httr", "tidyr", "dplyr", "openxlsx", "fuzzyjoin")
new.packages <- list.of.packages[!(list.of.packages %in% installed.packages()[,"Package"])]
if(length(new.packages)) install.packages(new.packages)

library(jsonlite)
library(httr)
library(tidyr)
library(dplyr)
library(openxlsx)
library(fuzzyjoin)

# Load CATAPULT_TOKEN from project .env (same as Python scripts). Requires R >= 4.0.
if (file.exists(".env")) {
  readRenviron(".env")
}

### Set Up Token To Get Data ###

token_raw <- Sys.getenv("CATAPULT_TOKEN")
if (token_raw == "") {
  stop("Set CATAPULT_TOKEN in .env (project root) or your environment before running.")
}
Token <- paste("Bearer", token_raw)

base_url <- Sys.getenv("CATAPULT_BASE_URL", "https://connect-au.catapultsports.com/api/v6")
base_url <- sub("/+$", "", base_url)


### Get All Activities ###

activity_list_url <- paste0(base_url, "/activities")
response <- VERB("GET", activity_list_url, add_headers('authorization' = Token), content_type("application/octet-stream"), accept("application/json"))
content(response, "text")
rawToChar(response$content)
Activity_List <- fromJSON(rawToChar(response$content))
Activity_List <- Activity_List %>% mutate(date = as.Date(as.POSIXct(start_time, origin = "1970-01-01", tz = "UTC")))

##################################################################################################################################################################################################

### ENTER START AND END DATES IN YYYY-MM-DD ###

start_date = "XXXX-XX-XX"
end_date = "XXXX-XX-XX"


##################################################################################################################################################################################################

### Get The Date Filtered Activity List ###

Activity_List <- Activity_List %>% filter(date >= start_date) %>% filter(date <= end_date)


### Run The Loop To Get All Player Data From The Selected Dates

All_Players_Jump_Data <- tibble()

for(j in seq_along(Activity_List)){
  
  activity_id <- Activity_List$id[j]
  
  activity_name <- Activity_List$name[j]

  athlete_url <- paste0(base_url, "/activities/", activity_id, "/athletes")
  response <- VERB("GET", athlete_url, add_headers('authorization' = Token), content_type("application/octet-stream"), accept("application/json"))
  content(response, "text")
  rawToChar(response$content)
  Athlete_List <- fromJSON(rawToChar(response$content))
  
  Players_Jump_Data <- list()

  for(i in seq_along(Athlete_List)){
      
    athlete_id <- Athlete_List$id[i]
    
    jump_url <- paste0(base_url, "/activities/", activity_id, "/athletes/", athlete_id, "/events")
    queryString <- list(event_types = "basketball")
    response <- VERB("GET", jump_url, query = queryString, add_headers('authorization' = Token), content_type("application/octet-stream"), accept("application/json"))
    content(response, "text")
    rawToChar(response$content)
    Player_Jump_Data <- fromJSON(rawToChar(response$content))

    if (!is.null(Player_Jump_Data$data)) {
      Player_Jump_Data <- as_tibble(Player_Jump_Data)
      Player_Jump_Data <- Player_Jump_Data %>% mutate(activity_id = activity_id)
      Player_Jump_Data <- Player_Jump_Data %>% mutate(activity_name = activity_name)
      Player_Jump_Data <- Player_Jump_Data %>% select(activity_name, activity_id, everything())
      
      if ("data" %in% colnames(Player_Jump_Data)) {
        Player_Jump_Data <- Player_Jump_Data %>% unnest(cols = c(`data`))
      }
      
      if ("basketball" %in% colnames(Player_Jump_Data)) {
        Player_Jump_Data <- Player_Jump_Data %>% unnest(cols = c(`basketball`)) 
      }
      
      if ("jump_attribute" %in% colnames(Player_Jump_Data)) {
        Player_Jump_Data <- Player_Jump_Data %>% filter(jump_attribute > 0)
      }
      
      Players_Jump_Data[[length(Players_Jump_Data) + 1]] <- Player_Jump_Data
    } else {
      message(paste("No jump data for athlete", athlete_id, "in activity", activity_id))
    }
    
    
  }
  
  if (length(Players_Jump_Data) > 0) {
    All_Players_Jump_Data <- bind_rows(All_Players_Jump_Data, bind_rows(Players_Jump_Data))
  }
}

jump_spreadsheet <- createWorkbook()

addWorksheet(jump_spreadsheet, "Sheet1")

writeData(jump_spreadsheet, "Sheet1", All_Players_Jump_Data)

out_xlsx <- Sys.getenv("JUMP_EXPORT_XLSX", "jump_spreadsheet.xlsx")
saveWorkbook(jump_spreadsheet, file = out_xlsx, overwrite = TRUE)
message("Saved: ", normalizePath(out_xlsx, mustWork = FALSE))
