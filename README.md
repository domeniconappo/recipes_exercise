# Recipes

This is a simple REST api for users to manage recipes.
It has CRUD and filtering functionalities.
Any user can manage their own recipes while having access to all others' recipes.

## Tech stack

- FastAPI and SQLModel
- PostgreSQL
- Docker/Docker compose


## How to run

The repository uses docker compose for local dev and testing.
Ensure you have docker compose installed before running these commands.

Copy the env file and edit it (if only for tests, defaults are fine):

`cp .env.example .env`

You can then start the app and the DB servers with:

`make run`

The app is available at http://localhost:8000.
Interactive API docs: http://localhost:8000/docs.

To tear down services:

`make stop`

To run tests:

`make test`


## Endpoints

### Auth — `/api/v1/auth`

| Method | Path        | Auth     | Description                                 |
|--------|-------------|----------|---------------------------------------------|
| `POST` | `/register` | —        | Create account                              |
| `POST` | `/login`    | —        | Get access + refresh tokens                 |
| `POST` | `/refresh`  | —        | Exchange refresh token for new access token |
| `GET`  | `/me`       | required | Get current user                            |

### Recipes — `/api/v1/recipes`

| Method   | Path            | Auth             | Description             |
|----------|-----------------|------------------|-------------------------|
| `GET`    | `/recipes`      | —                | List and filter recipes |
| `POST`   | `/recipes`      | required         | Create a recipe         |
| `GET`    | `/recipes/{id}` | —                | Get a recipe by ID      |
| `PUT`    | `/recipes/{id}` | required (owner) | update                  |
| `DELETE` | `/recipes/{id}` | required (owner) | Delete                  |

### Filtering (`GET /recipes`)

All query parameters are optional and combinable.

| Parameter             | Type                | Description                                        |
|-----------------------|---------------------|----------------------------------------------------|
| `vegetarian`          | bool                | `true` or `false`                                  |
| `servings`            | int                 | Exact number of servings                           |
| `include_ingredients` | string (repeatable) | Recipe must contain ALL listed ingredients         |
| `exclude_ingredients` | string (repeatable) | Recipe must contain NONE of the listed ingredients |
| `instructions_search` | string              | Case-insensitive substring match on instructions   |
| `page`                | int                 | Page number (default: 1)                           |
| `page_size`           | int                 | Results per page, max 100 (default: 20)            |

**Examples:**

```
GET /api/v1/recipes?vegetarian=true
GET /api/v1/recipes?servings=4&include_ingredients=potatoes
GET /api/v1/recipes?exclude_ingredients=salmon&instructions_search=oven
```

## Environment Variables

| Variable                      | Description                                       |
|-------------------------------|---------------------------------------------------|
| `DATABASE_URL`                | Async PostgreSQL URL (`postgresql+asyncpg://...`) |
| `SECRET_KEY`                  | JWT signing secret (min 32 chars)                 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL (default: 15)                    |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | Refresh token TTL (default: 7)                    |
| `APP_ENV`                     | `development` (enables SQL query logging)         |


## Project structure

app/
├── config.py          # Settings from environment variables
├── database.py
├── main.py
├── models/
│   ├── user.py        # User SQLModel table
│   └── recipe.py      # Recipe + RecipeIngredient SQLModel tables
├── schemas/
│   ├── auth.py        # Request/response schemas for auth
│   └── recipe.py      # Request/response/filter schemas for recipes
├── routers/
│   ├── auth.py        # Auth endpoints
│   └── recipes.py     # Recipe endpoints
└── services/
    ├── auth.py        # user auth operations with JWT
    └── recipe.py      # Recipe CRUD and filtering