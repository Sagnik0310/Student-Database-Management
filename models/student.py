class student:
    def __init__(self,reg_no,roll_no,name,age,branch):
        self.reg_no = reg_no
        self.roll_no = roll_no
        self.name = name
        self.age = age
        self.branch = branch
    def __str__(self):
        return f"Reg:{self.reg_no} | Roll: {self.roll_no} | Name: {self.name} | Age: {self.age} | Branch: {self.branch}"