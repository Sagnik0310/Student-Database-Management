class Student:

    def __init__(self, reg_no, roll_no, name, age, branch):

        self.reg_no = reg_no
        self.roll_no = roll_no
        self.name = name
        self.age = age
        self.branch = branch

    def __str__(self):

        return (
            f"Reg: {self.reg_no} | "
            f"Roll: {self.roll_no} | "
            f"Name: {self.name} | "
            f"Age: {self.age} | "
            f"Branch: {self.branch}"
        )