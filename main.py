import pandas as pd

df = pd.read_csv("viral_load_samples_2024.csv")


class  Student:
    def __init__(self, name):
        self.name = name 
        self.__grade = 0
    def set_grade(self, grade):
        if 0 <= grade <= 100:
            self.__grade = grade
        else:
            print ("Grade must be between 0 and 100")\

    def get_grade(self):
        return self.__grade
    def get_status(self):
        if self.__grade >= 60:
            return "Passes"
        else :
            return "failed"

student = Student("Emil")
student.set_grade(85)
print(student.get_grade())
print(student.get_status())
    