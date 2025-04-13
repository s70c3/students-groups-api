from fastapi import FastAPI, HTTPException, Depends, Query
from sqlalchemy import Column, Integer, String, ForeignKey, create_engine
from sqlalchemy.orm import sessionmaker, relationship, declarative_base, Session
from typing import Optional, List
from pydantic import BaseModel
from fastapi import status
from fastapi.responses import JSONResponse
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/postgres")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI()

# SQLAlchemy models
class Group(Base):
    __tablename__ = 'groups'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    parent_id = Column(Integer, ForeignKey('groups.id'), nullable=True)

    # рекурсивная связь
    subgroups = relationship(
        "Group",
        backref='parent',
        remote_side=[id],
        lazy="selectin"  # 🔥 ЗАГРУЖАЕМ ДЕТЕЙ ПРИ ЗАПРОСЕ РОДИТЕЛЯ
    )

    students = relationship("Student", back_populates="group")


class Student(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String)
    group_id = Column(Integer, ForeignKey('groups.id'))

    group = relationship("Group", back_populates="students")

# Pydantic schemas
class GroupBase(BaseModel):
    name: str
    parent_id: Optional[int] = None

class GroupCreate(GroupBase):
    pass

class GroupOut(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    subGroups: List['GroupOut'] = []

    class Config:
        from_attributes = True

GroupOut.model_rebuild()

class GroupFlatOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class StudentBase(BaseModel):
    name: str
    email: str
    group_id: int

class StudentCreate(StudentBase):
    pass

class StudentOut(BaseModel):
    id: int
    name: str
    group_id: int

    class Config:
        from_attributes = True

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CRUD endpoints
@app.post("/students", response_model=StudentOut)
def create_student(student: StudentCreate, db: Session = Depends(get_db)):
    db_student = Student(**student.dict())
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student

@app.get("/students", response_model=List[StudentOut])
def get_students(query: Optional[str] = Query(None), db: Session = Depends(get_db)):
    q = db.query(Student)
    if query:
        q = q.join(Group).filter((Student.name.ilike(f"%{query}%")) | (Group.name.ilike(f"%{query}%")))
    return q.all()

@app.get("/students/{student_id}", response_model=StudentOut)
def get_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student

@app.put("/students/{student_id}", response_model=StudentOut)
def update_student(student_id: int, student: StudentCreate, db: Session = Depends(get_db)):
    db_student = db.query(Student).filter(Student.id == student_id).first()
    if not db_student:
        raise HTTPException(status_code=404, detail="Student not found")
    for field, value in student.dict().items():
        setattr(db_student, field, value)
    db.commit()
    return db_student

@app.delete("/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    db.delete(student)
    db.commit()
    return {"message": "Student deleted"}

@app.post("/groups", response_model=GroupOut)
def create_group(group: GroupCreate, db: Session = Depends(get_db)):
    data = group.dict()
    if data["parent_id"] == 0:
        data["parent_id"] = None
    db_group = Group(**data)
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group
@app.get("/groups")
def get_groups(query: Optional[str] = Query(None), db: Session = Depends(get_db)):
    if query:
        # Поиск по имени (плоский список)
        results = db.query(Group).filter(Group.name.ilike(f"%{query}%")).all()
        return JSONResponse(content=[{"id": g.id, "name": g.name} for g in results])

    # Полное дерево
    groups = db.query(Group).all()
    # Группируем по parent_id
    from collections import defaultdict

    # Группировка: parent_id → [subgroups]
    children_map = defaultdict(list)
    for group in groups:
        children_map[group.parent_id].append(group)

    def build_tree(group: Group) -> GroupOut:
        return GroupOut(
            id=group.id,
            name=group.name,
            parent_id=group.parent_id,
            subGroups=[build_tree(child) for child in children_map.get(group.id, [])]
        )

    roots = children_map[None]
    return [build_tree(root) for root in roots]


@app.get("/groups/{group_id}", response_model=GroupOut)
def get_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group

@app.put("/groups/{group_id}", response_model=GroupOut)
def update_group(group_id: int, group: GroupOut, db: Session = Depends(get_db)):
    if group.id != group_id:
        raise HTTPException(
            status_code=400,
            detail="ID in path and body must match"
        )

    db_group = db.query(Group).filter(Group.id == group_id).first()
    if not db_group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Нельзя быть родителем самому себе
    if group.parent_id == group_id:
        raise HTTPException(
            status_code=400,
            detail="Group cannot be its own parent"
        )

    # Если указан parent_id — проверим его существование
    if group.parent_id is not None:
        parent = db.query(Group).filter(Group.id == group.parent_id).first()
        if not parent:
            raise HTTPException(
                status_code=400,
                detail=f"Parent group with id {group.parent_id} not found"
            )

    db_group.name = group.name
    db_group.parent_id = group.parent_id
    db.commit()
    db.refresh(db_group)
    return db_group



@app.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Проверка: есть ли подгруппы
    has_children = db.query(Group).filter(Group.parent_id == group_id).first()
    if has_children:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete group with existing subgroups"
        )

    db.delete(group)
    db.commit()

# Create tables
Base.metadata.create_all(bind=engine)
