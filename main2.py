from fastapi import FastAPI, status, HTTPException
from fastapi.params import Depends
from sqlalchemy.orm import Session
from schemas import Product, DisplayProduct, Seller, DisplaySeller, Login, TokenData
import models
from database import engine, SessionLocal
import uvicorn
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY = "INSERT HERE"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 20

app = FastAPI(
    title="Products API",
    description="Get details for all the products on our website",
    terms_of_service="http://www.google.com",
    contact={"Developer name": "William Cezar"}

)

models.Base.metadata.create_all(engine)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def gererate_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encode_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=[ALGORITHM])
    return encode_jwt


@app.post('/login')
def login(request: Login, db: Session = Depends(get_db)):
    seller = db.query(models.Seller).filter(models.Seller.username == request.username).first()
    if not seller:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Username not found')
    if not pwd_context.verify(request.password, seller.password):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Invalid password')
    access_token = gererate_token(
        data={"sub": seller.username}
    )
    return {"access_token": access_token, "token_type": "bearer"}


def get_current_user(token: str=Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_226_IM_USED,
        detail="Invalid credential",
        headers={'WWW-Authenticate: "Bearer'}
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithm=[ALGORITHM])
        username: str = payload.get('sub')
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception


@app.delete('/product/{id}', tags=['Products'])
def delete(id, db: Session = Depends(get_db)):
    db.query(models.Product).filter(models.Product.id == id).delete(synchronize_session=False)
    db.commit()
    return "product deleted"


@app.get('/products', tags=['Products'])
def products(db: Session = Depends(get_db)):
    products = db.query(models.Product).all()
    return products


@app.get('/product/{id}', response_model=DisplayProduct, tags=['Products'])
def products(id, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == id).first()
    return product


@app.put('product/{id}', tags=['Products'])
def update(id, request: Product, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == id)
    if not product.first():
        pass
    product.update(request.dict())
    db.commit()
    return "Product updated"


@app.post('/product', tags=['Products'])
def add(request: Product, db: Session = Depends(get_db)):
    new_product = models.Product(name=request.name, description=request.description, price=request.price, seller_id=1)
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return request


@app.post('/seller', response_model=DisplaySeller, tags=['Sellers'])
def create_seller(request: Seller, db: Session = Depends(get_db)):
    encript_pass = pwd_context.hash(request.password)
    new_seller = models.Seller(username=request.username, email=request.email, password=encript_pass)
    db.add(new_seller)
    db.commit()
    db.refresh(new_seller)
    return new_seller


uvicorn.run(app, host="0.0.0.0", port=1010)