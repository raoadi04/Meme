import os
import yaml
from fastapi import FastAPI, UploadFile, Depends, HTTPException
from sqlalchemy.orm import Session
from embedchain import Pipeline as App
from embedchain.client import Client
from models import (
    QueryApp,
    SourceApp,
    MessageApp,
    DefaultResponse,
    DeployAppRequest,
    # SetEnvKeys,
)
from database import Base, engine, SessionLocal
from services import get_app, save_app, get_apps, remove_app

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI(
    title="Embedchain REST API",
    description="This is the REST API for Embedchain.",
    version="0.0.1",
    license_info={
        "name": "Apache 2.0",
        "url": "https://github.com/embedchain/embedchain/blob/main/LICENSE",
    },
)


@app.get("/ping", tags=["Utility"])
def check_status():
    """
    Endpoint to check the status of the API.
    """
    return {"ping": "pong"}


# FIXME: Put on hold for now
# @app.put("/env", tags=["Apps"])
# async def set_env(body: SetEnvKeys):
#     """
#     Set the Environment variables needed for respective LLMs to work.\n
#     """
#     keys = body.keys
#     try:
#         for key in keys:
#             os.environ[key] = keys[key]

#         return DefaultResponse(response="Env variables set successfully.")
#     except Exception as e:
#         raise HTTPException(detail=f"Error setting API key: {e}", status_code=400)


@app.get("/apps", tags=["Apps"])
async def get_all_apps(db: Session = Depends(get_db)):
    """
    Get all apps.
    """
    apps = get_apps(db)
    return {"data": apps}


@app.post("/create", tags=["Apps"], response_model=DefaultResponse)
async def create_app_using_default_config(app_id: str, db: Session = Depends(get_db)):
    """
    Create a new app using App ID.
    This uses a default config
    i.e, our opensource config that doesn't require any API key to run.\n
    """
    try:
        if app_id is None:
            raise HTTPException(detail="App ID not provided.", status_code=400)

        if get_app(db, app_id) is not None:
            raise HTTPException(detail=f"App with id '{app_id}' already exists.", status_code=400)

        yaml_path = "default.yaml"

        save_app(db, app_id, yaml_path)

        return DefaultResponse(response=f"App created successfully. App ID: {app_id}")
    except Exception as e:
        raise HTTPException(detail=f"Error creating app: {e}", status_code=400)


@app.post("/create/yaml", tags=["Apps"], response_model=DefaultResponse)
async def create_app_using_custom_config(config: UploadFile, db: Session = Depends(get_db)):
    """
    Create a new app using YAML config.
    """
    try:
        contents = await config.read()

        try:
            yaml_conf = yaml.safe_load(contents)
            app_id = yaml_conf.get("app", {}).get("config", {}).get("id", None)

            if app_id is None:
                raise HTTPException(detail="App ID not provided.", status_code=400)

            if get_app(db, app_id) is not None:
                raise HTTPException(detail=f"App with id '{app_id}' already exists.", status_code=400)

            yaml_path = f"configs/{app_id}.yaml"
            with open(yaml_path, "w") as file:
                file.write(str(contents, "utf-8"))

            save_app(db, app_id, yaml_path)

        except yaml.YAMLError as exc:
            raise HTTPException(detail=f"Error parsing YAML: {exc}", status_code=400)

        return DefaultResponse(response=f"App created successfully. App ID: {app_id}")
    except Exception as e:
        raise HTTPException(detail=f"Error creating app: {e}", status_code=400)


@app.get(
    "/{app_id}/datasources",
    tags=["Apps"],
)
async def get_datasources_associated_with_app_id(app_id: str, db: Session = Depends(get_db)):
    """
    Get all datasources for an app.\n
    app_id: The ID of the app. Use "default" for the default app.\n
    """
    try:
        if app_id is None:
            raise HTTPException(
                detail="App ID not provided. If you want to use the default app, use 'default' as the app_id.",
                status_code=400,
            )

        db_app = get_app(db, app_id)

        if db_app is None:
            raise HTTPException(detail=f"App with id {app_id} does not exist, please create it first.", status_code=400)

        app = App.from_config(yaml_path=db_app.config)

        response = app.get_data_sources_by_app_id(app_id=app_id)
        return {"data": response}
    except ValueError as ve:
        if "OPENAI_API_KEY" in str(ve) or "OPENAI_ORGANIZATION" in str(ve):
            raise HTTPException(
                detail="OPENAI_API_KEY or OPENAI_ORGANIZATION not set, please set them in your environment variables.",
                status_code=400,
            )
    except Exception as e:
        raise HTTPException(detail=f"Error occurred: {e}", status_code=400)


@app.post(
    "/{app_id}/add",
    tags=["Apps"],
    response_model=DefaultResponse,
)
async def add_datasource_to_an_app(body: SourceApp, app_id: str, db: Session = Depends(get_db)):
    """
    Add a source to an existing app.\n
    app_id: The ID of the app. Use "default" for the default app.\n
    source: The source to add.\n
    data_type: The data type of the source. Remove it if you want Embedchain to detect it automatically.\n
    """
    try:
        if app_id is None:
            raise HTTPException(
                detail="App ID not provided. If you want to use the default app, use 'default' as the app_id.",
                status_code=400,
            )

        db_app = get_app(db, app_id)

        if db_app is None:
            raise HTTPException(detail=f"App with id {app_id} does not exist, please create it first.", status_code=400)

        app = App.from_config(yaml_path=db_app.config)

        response = app.add(source=body.source, data_type=body.data_type)
        return DefaultResponse(response=response)
    except ValueError as ve:
        if "OPENAI_API_KEY" in str(ve) or "OPENAI_ORGANIZATION" in str(ve):
            raise HTTPException(
                detail="OPENAI_API_KEY or OPENAI_ORGANIZATION not set, please set them in your environment variables.",
                status_code=400,
            )
    except Exception as e:
        raise HTTPException(detail=f"Error occurred: {e}", status_code=400)


@app.post(
    "/{app_id}/query",
    tags=["Apps"],
    response_model=DefaultResponse,
)
async def query_an_app(body: QueryApp, app_id: str, db: Session = Depends(get_db)):
    """
    Query an existing app.\n
    app_id: The ID of the app. Use "default" for the default app.\n
    query: The query that you want to ask the App.\n
    """
    try:
        if app_id is None:
            raise HTTPException(
                detail="App ID not provided. If you want to use the default app, use 'default' as the app_id.",
                status_code=400,
            )

        db_app = get_app(db, app_id)

        if db_app is None:
            raise HTTPException(detail=f"App with id {app_id} does not exist, please create it first.", status_code=400)

        app = App.from_config(yaml_path=db_app.config)

        response = app.query(body.query)
        return DefaultResponse(response=response)
    except ValueError as ve:
        if "OPENAI_API_KEY" in str(ve) or "OPENAI_ORGANIZATION" in str(ve):
            raise HTTPException(
                detail="OPENAI_API_KEY or OPENAI_ORGANIZATION not set, please set them in your environment variables.",
                status_code=400,
            )
    except Exception as e:
        raise HTTPException(detail=f"Error occurred: {e}", status_code=400)


@app.post(
    "/{app_id}/chat",
    tags=["Apps"],
    response_model=DefaultResponse,
)
async def chat_with_an_app(body: MessageApp, app_id: str, db: Session = Depends(get_db)):
    """
    Query an existing app.\n
    app_id: The ID of the app. Use "default" for the default app.\n
    message: The message that you want to send to the App.\n
    """
    try:
        if app_id is None:
            raise HTTPException(
                detail="App ID not provided. If you want to use the default app, use 'default' as the app_id.",
                status_code=400,
            )

        db_app = get_app(db, app_id)

        if db_app is None:
            raise HTTPException(detail=f"App with id {app_id} does not exist, please create it first.", status_code=400)

        app = App.from_config(yaml_path=db_app.config)

        response = app.chat(body.message)
        return DefaultResponse(response=response)
    except ValueError as ve:
        if "OPENAI_API_KEY" in str(ve) or "OPENAI_ORGANIZATION" in str(ve):
            raise HTTPException(
                detail="OPENAI_API_KEY or OPENAI_ORGANIZATION not set, please set them in your environment variables.",
                status_code=400,
            )
    except Exception as e:
        raise HTTPException(detail=f"Error occurred: {e}", status_code=400)


@app.post(
    "/{app_id}/deploy",
    tags=["Apps"],
    response_model=DefaultResponse,
)
async def deploy_app(body: DeployAppRequest, app_id: str, db: Session = Depends(get_db)):
    """
    Query an existing app.\n
    app_id: The ID of the app. Use "default" for the default app.\n
    api_key: The API key to use for deployment. If not provided,
    Embedchain will use the API key previously used (if any).\n
    """
    try:
        if app_id is None:
            raise HTTPException(
                detail="App ID not provided. If you want to use the default app, use 'default' as the app_id.",
                status_code=400,
            )

        db_app = get_app(db, app_id)

        if db_app is None:
            raise HTTPException(detail=f"App with id {app_id} does not exist, please create it first.", status_code=400)

        app = App.from_config(yaml_path=db_app.config)

        api_key = body.api_key
        # this will save the api key in the embedchain.db
        Client(api_key=api_key)

        app.deploy()
        return DefaultResponse(response="App deployed successfully.")
    except ValueError as ve:
        if "OPENAI_API_KEY" in str(ve) or "OPENAI_ORGANIZATION" in str(ve):
            raise HTTPException(
                detail="OPENAI_API_KEY or OPENAI_ORGANIZATION not set, please set them in your environment variables.",
                status_code=400,
            )
    except Exception as e:
        raise HTTPException(detail=f"Error occurred: {e}", status_code=400)


@app.delete(
    "/{app_id}/delete",
    tags=["Apps"],
    response_model=DefaultResponse,
)
async def delete_app(app_id: str, db: Session = Depends(get_db)):
    """
    Delete an existing app.\n
    app_id: The ID of the app to be deleted.
    """
    try:
        if app_id is None:
            raise HTTPException(
                detail="App ID not provided. If you want to use the default app, use 'default' as the app_id.",
                status_code=400,
            )

        db_app = get_app(db, app_id)

        if db_app is None:
            raise HTTPException(detail=f"App with id {app_id} does not exist, please create it first.", status_code=400)

        app = App.from_config(yaml_path=db_app.config)

        # reset app.db
        app.db.reset()

        remove_app(db, app_id)
        return DefaultResponse(response=f"App with id {app_id} deleted successfully.")
    except Exception as e:
        raise HTTPException(detail=f"Error occurred: {e}", status_code=400)


if __name__ == "__main__":
    import uvicorn

    is_dev = os.getenv("DEVELOPMENT", "False")
    uvicorn.run("main:app", host="0.0.0.0", port=8010, reload=bool(is_dev))
