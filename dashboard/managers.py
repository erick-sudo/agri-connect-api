from django.contrib.auth.base_user import BaseUserManager

class CustomUserManager(BaseUserManager):
        
    def create_user(self, first_name, last_name, email, phone, password):
        """ Create and save user with the given first name, last name, email, phone number and password."""
        
        if not email:
            raise ValueError("Users must have Email")
        
        if not phone:
            raise ValueError("Users must have a Phone number")
        
        if not first_name or not last_name:
            raise ValueError("Users must have a First and Last name")
        
        user = self.model(
            first_name = first_name,
            last_name = last_name,
            email = self.normalize_email(email),
            phone = phone,
        )
        user.set_password(password)
        user.save(using = self._db)
        
        return user
    def create_staff_user(self, first_name, last_name, email, phone, password):
        """ Create and save superuser with the given first name, last name, email, phone number and password."""
        
        user = self.create_user(first_name, last_name, email, phone, password)
        user.is_staff=True
        user.save(using = self._db)
        
        return user
    def create_superuser(self, first_name, last_name, email, phone, password):
        """ Create and save superuser with the given first name, last name, email, phone number and password."""
        
        user = self.create_user(first_name, last_name, email, phone, password)
        user.is_superuser=True
        user.is_staff=True
        user.save(using = self._db)
        
        return user

