from django.contrib.auth import password_validation as base


class UserAttributeSimilarityValidator(base.UserAttributeSimilarityValidator):
    def get_error_message(self):
        return "Parol shaxsiy ma'lumotlaringizga (telefon, ism, familiya) juda o'xshash."

    def get_help_text(self):
        return "Parol shaxsiy ma'lumotlaringizga o'xshamasligi kerak."


class MinimumLengthValidator(base.MinimumLengthValidator):
    def get_error_message(self):
        return f"Parol kamida {self.min_length} ta belgidan iborat bo'lishi kerak."

    def get_help_text(self):
        return f"Parol kamida {self.min_length} ta belgidan iborat bo'lsin."


class CommonPasswordValidator(base.CommonPasswordValidator):
    def get_error_message(self):
        return "Bu parol juda oddiy — uni topish oson."

    def get_help_text(self):
        return "Parol keng tarqalgan parollardan bo'lmasligi kerak."


class NumericPasswordValidator(base.NumericPasswordValidator):
    def get_error_message(self):
        return "Parol faqat raqamlardan iborat bo'lmasligi kerak."

    def get_help_text(self):
        return "Parolda harf ham bo'lsin, faqat raqam bo'lmasin."
