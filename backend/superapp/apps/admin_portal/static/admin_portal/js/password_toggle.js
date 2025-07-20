document.addEventListener('DOMContentLoaded', function() {
  // Find all password toggle buttons
  const toggleButtons = document.querySelectorAll('.password-toggle-btn');
  
  // Add click event listener to each button
  toggleButtons.forEach(button => {
    button.addEventListener('click', function() {
      // Get the target input field
      const targetId = this.getAttribute('data-target-id');
      const passwordInput = document.getElementById(targetId);
      
      if (!passwordInput) return;
      
      // Toggle between password and text type
      if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        this.querySelector('.eye-open').classList.add('hidden');
        this.querySelector('.eye-closed').classList.remove('hidden');
      } else {
        passwordInput.type = 'password';
        this.querySelector('.eye-open').classList.remove('hidden');
        this.querySelector('.eye-closed').classList.add('hidden');
      }
    });
  });
});
